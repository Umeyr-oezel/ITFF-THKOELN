"""Database models for the SEC Form 4 pipeline.

These mirror the seven tables the pipeline used to create with raw SQL.
submissions is the parent; the four transaction/holding tables hang off
it via a real foreign key (CASCADE), so deleting a filing now cleans up
its children automatically - something the old code had to do by hand
because the shared MySQL server wouldn't grant REFERENCES.

validation_log and pipeline_log stand on their own. pipeline_log in
particular is an audit trail that the pipeline never deletes.
"""
from django.db import models


class Submission(models.Model):
    """One SEC Form 4 filing - the parent every transaction points back to.

    accession_number is the natural primary key straight from SEC, so we
    use it directly instead of a surrogate id. The is_* flags describe the
    reporting owner's relationship to the issuer (director, officer, etc.).
    """
    accession_number = models.CharField(max_length=30, primary_key=True)
    filing_date = models.DateField(null=True)
    issuer_cik = models.BigIntegerField(null=True)
    issuer_name = models.CharField(max_length=255, null=True)
    issuer_ticker = models.CharField(max_length=20, null=True)
    rptowner_cik = models.BigIntegerField(null=True)
    rptowner_name = models.CharField(max_length=255, null=True)
    is_director = models.BooleanField(null=True)
    is_officer = models.BooleanField(null=True)
    is_ten_percent = models.BooleanField(null=True)
    is_other = models.BooleanField(null=True)
    officer_title = models.CharField(max_length=255, null=True)
    created_by = models.CharField(max_length=50)
    source_quarter = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "submissions"
        indexes = [
            models.Index(fields=["issuer_cik"], name="idx_issuer_cik"),
            models.Index(fields=["source_quarter"], name="idx_sub_source_quarter"),
            models.Index(fields=["filing_date"], name="idx_filing_date"),
        ]

    def __str__(self):
        """Identify a filing by its accession number - the only field
        that's guaranteed unique and meaningful on its own."""
        return self.accession_number


class NonderivTrans(models.Model):
    """A non-derivative transaction (e.g. a plain stock buy or sell).

    is_valid and validation_flags stay empty until the validation phase
    fills them in - that's why both are nullable with no default.
    """
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        db_column="accession_number", related_name="nonderiv_trans",
    )
    trans_date = models.DateField(null=True)
    trans_code = models.CharField(max_length=5, null=True)
    equity_swap = models.CharField(max_length=5, null=True)
    shares = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    price_per_share = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    shares_owned_following = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    nominal_volume = models.DecimalField(max_digits=24, decimal_places=4, null=True)
    is_valid = models.BooleanField(null=True, default=None)
    validation_flags = models.CharField(max_length=500, null=True, default=None)
    created_by = models.CharField(max_length=50)
    source_quarter = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nonderiv_trans"
        indexes = [
            models.Index(fields=["trans_code"], name="idx_nd_trans_code"),
            models.Index(fields=["trans_date"], name="idx_nd_trans_date"),
            models.Index(fields=["source_quarter"], name="idx_nd_source_quarter"),
        ]


class NonderivHolding(models.Model):
    """A non-derivative holding snapshot - shares owned at filing time."""
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        db_column="accession_number", related_name="nonderiv_holdings",
    )
    shares_owned = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    created_by = models.CharField(max_length=50)
    source_quarter = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nonderiv_holdings"
        indexes = [
            models.Index(fields=["source_quarter"], name="idx_ndh_source_quarter"),
        ]


class DerivTrans(models.Model):
    """A derivative transaction (options, warrants, convertibles).

    Same shape as NonderivTrans - SEC splits derivative and non-derivative
    activity into separate tables, so we keep them apart too.
    """
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        db_column="accession_number", related_name="deriv_trans",
    )
    trans_date = models.DateField(null=True)
    trans_code = models.CharField(max_length=5, null=True)
    equity_swap = models.CharField(max_length=5, null=True)
    shares = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    price_per_share = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    shares_owned_following = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    nominal_volume = models.DecimalField(max_digits=24, decimal_places=4, null=True)
    is_valid = models.BooleanField(null=True, default=None)
    validation_flags = models.CharField(max_length=500, null=True, default=None)
    created_by = models.CharField(max_length=50)
    source_quarter = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "deriv_trans"
        indexes = [
            models.Index(fields=["trans_date"], name="idx_d_trans_date"),
            models.Index(fields=["source_quarter"], name="idx_d_source_quarter"),
        ]


class DerivHolding(models.Model):
    """A derivative holding snapshot - mirrors NonderivHolding."""
    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE,
        db_column="accession_number", related_name="deriv_holdings",
    )
    shares_owned = models.DecimalField(max_digits=20, decimal_places=4, null=True)
    created_by = models.CharField(max_length=50)
    source_quarter = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "deriv_holdings"
        indexes = [
            models.Index(fields=["source_quarter"], name="idx_dh_source_quarter"),
        ]


class ValidationLog(models.Model):
    """One row per failed validation check, for traceability.

    accession_number is stored as a plain string rather than a foreign
    key: a check can flag an orphan record whose submission doesn't exist,
    and we still want to log that.
    """
    accession_number = models.CharField(max_length=30, null=True)
    table_name = models.CharField(max_length=50)
    record_id = models.IntegerField(null=True)
    check_name = models.CharField(max_length=100)
    is_passed = models.BooleanField()
    details = models.TextField(null=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    source_quarter = models.CharField(max_length=10)

    class Meta:
        db_table = "validation_log"
        indexes = [
            models.Index(fields=["accession_number"], name="idx_vlog_accession"),
            models.Index(fields=["source_quarter"], name="idx_vlog_source_quarter"),
        ]


class PipelineLog(models.Model):
    """Audit trail of every pipeline run. Never deleted.

    Unlike the data tables, rows here accumulate across re-runs so we
    keep a full history of what ran, when, and whether it succeeded.
    """
    run_timestamp = models.DateTimeField(auto_now_add=True)
    quarter_processed = models.CharField(max_length=10, null=True)
    table_name = models.CharField(max_length=50, null=True)
    records_imported = models.IntegerField(default=0)
    records_invalid = models.IntegerField(default=0)
    status = models.CharField(max_length=20)
    duration_seconds = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    error_message = models.TextField(null=True)

    class Meta:
        db_table = "pipeline_log"
