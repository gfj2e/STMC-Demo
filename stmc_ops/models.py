import uuid

from django.db import models
from django.db.models import Q


class UserRole(models.TextChoices):
	EXECUTIVE = "executive", "Executive"
	DIVISION_MANAGER = "division_manager", "Division Manager"
	SALES = "sales", "Sales"
	CONTRACTS = "contracts", "Contracts"
	PROJECT_MANAGER = "project_manager", "Project Manager"


class RegionCode(models.TextChoices):
	SUMMERTOWN = "summertown", "Summertown"
	EAST_TN = "east_tn", "East Tennessee"
	HOPKINSVILLE = "hopkinsville", "Hopkinsville"


class ContractStatus(models.TextChoices):
	DRAFT = "draft", "Draft"
	REVIEW = "review", "Review"
	SENT = "sent", "Sent"
	SIGNED = "signed", "Signed"
	ACTIVE = "active", "Active"
	COMPLETE = "complete", "Complete"
	CANCELLED = "cancelled", "Cancelled"


class DrawCalcMethod(models.TextChoices):
	FIXED_AMOUNT = "fixed_amount", "Fixed Amount"
	PERCENTAGE = "percentage", "Percentage"


class DrawStatus(models.TextChoices):
	PENDING = "pending", "Pending"
	PHASE_COMPLETE = "phase_complete", "Phase Complete"
	INVOICED = "invoiced", "Invoiced"
	PAID = "paid", "Paid"
	OVERDUE = "overdue", "Overdue"


class ChangeOrderStatus(models.TextChoices):
	DRAFT = "draft", "Draft"
	PENDING_APPROVAL = "pending_approval", "Pending Approval"
	APPROVED = "approved", "Approved"
	SENT = "sent", "Sent"
	SIGNED = "signed", "Signed"
	REJECTED = "rejected", "Rejected"


class MetricSource(models.TextChoices):
	PLAN_SCHEDULE = "plan_schedule", "Plan Schedule"
	COMPUTED = "computed", "Computed"
	MANUAL = "manual", "Manual"


class EditScope(models.TextChoices):
	BASE = "base", "Base"
	UPGRADE = "upgrade", "Upgrade"


class Region(models.Model):
	id = models.CharField(max_length=32, primary_key=True, choices=RegionCode.choices)
	name = models.TextField()
	description = models.TextField(blank=True, null=True)
	labor_mileage_multiplier = models.DecimalField(max_digits=5, decimal_places=4, default=1.0000)
	concrete_rate_per_sf = models.DecimalField(max_digits=8, decimal_places=2, default=8.00)
	turnkey_sf_premium = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
	interior_regional_adder = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "regions"

	def __str__(self):
		return self.name


class OpsUser(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	email = models.EmailField(unique=True)
	password_hash = models.TextField()
	first_name = models.TextField()
	last_name = models.TextField()
	role = models.CharField(max_length=32, choices=UserRole.choices)
	region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "users"
		indexes = [
			models.Index(fields=["role"], name="idx_users_role"),
			models.Index(fields=["region"], name="idx_users_region"),
		]

	def __str__(self):
		return f"{self.first_name} {self.last_name}".strip()


class ModelCatalog(models.Model):
	name = models.TextField(unique=True)
	name_normalized = models.TextField(unique=True)
	square_footage = models.IntegerField()
	mft_percentage = models.DecimalField(max_digits=5, decimal_places=4)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "models"

	def __str__(self):
		return self.name


class MetricDefinition(models.Model):
	field_key = models.TextField(unique=True)
	label = models.TextField()
	unit = models.TextField(default="SF")
	source = models.CharField(max_length=32, choices=MetricSource.choices)
	compute_formula = models.TextField(blank=True, null=True)
	depends_on = models.JSONField(blank=True, null=True)
	category = models.TextField(default="general")
	display_order = models.IntegerField(default=0)
	is_overridable = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "metric_definitions"

	def __str__(self):
		return self.field_key


class ModelDefaultMetric(models.Model):
	model = models.ForeignKey(ModelCatalog, on_delete=models.CASCADE, related_name="default_metrics")
	metric = models.ForeignKey(
		MetricDefinition,
		to_field="field_key",
		db_column="metric_key",
		on_delete=models.CASCADE,
		related_name="model_defaults",
	)
	default_value = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)

	class Meta:
		db_table = "model_default_metrics"
		constraints = [
			models.UniqueConstraint(fields=["model", "metric"], name="model_default_metrics_model_metric_uniq"),
		]
		indexes = [
			models.Index(fields=["model"], name="idx_model_metrics_model"),
		]


class RateCardVersion(models.Model):
	region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="rate_card_versions")
	version_label = models.TextField()
	effective_date = models.DateField()
	is_current = models.BooleanField(default=True)
	notes = models.TextField(blank=True, null=True)
	created_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_rate_card_versions")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "rate_card_versions"
		constraints = [
			models.UniqueConstraint(fields=["region", "version_label"], name="rate_card_versions_region_label_uniq"),
			models.UniqueConstraint(
				fields=["region"],
				condition=Q(is_current=True),
				name="rate_card_versions_one_current_per_region",
			),
		]
		indexes = [
			models.Index(fields=["region"], name="idx_rate_versions_region"),
			models.Index(fields=["region", "is_current"], name="idx_rate_versions_current"),
		]


class RateCardItem(models.Model):
	version = models.ForeignKey(RateCardVersion, on_delete=models.CASCADE, related_name="items")
	rate_key = models.TextField()
	label = models.TextField()
	rate = models.DecimalField(max_digits=12, decimal_places=4)
	unit = models.TextField()
	driver = models.TextField()
	category = models.TextField()
	trade_group = models.TextField()
	display_order = models.IntegerField(default=0)

	class Meta:
		db_table = "rate_card_items"
		constraints = [
			models.UniqueConstraint(fields=["version", "rate_key"], name="rate_card_items_version_key_uniq"),
		]
		indexes = [
			models.Index(fields=["version"], name="idx_rate_items_version"),
		]


class ModelRegionalPricing(models.Model):
	model = models.ForeignKey(ModelCatalog, on_delete=models.CASCADE, related_name="regional_pricing")
	region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="model_pricing")
	material_price = models.DecimalField(max_digits=12, decimal_places=2)
	exterior_labor_rate = models.DecimalField(max_digits=12, decimal_places=2)
	concrete_price = models.DecimalField(max_digits=12, decimal_places=2)
	shell_price = models.DecimalField(max_digits=12, decimal_places=2)
	turnkey_per_sf = models.DecimalField(max_digits=8, decimal_places=2)
	turnkey_adder = models.DecimalField(max_digits=12, decimal_places=2)
	turnkey_total = models.DecimalField(max_digits=12, decimal_places=2)
	quote_id = models.TextField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "model_regional_pricing"
		constraints = [
			models.UniqueConstraint(fields=["model", "region"], name="model_regional_pricing_model_region_uniq"),
		]
		indexes = [
			models.Index(fields=["model"], name="idx_model_pricing_model"),
			models.Index(fields=["region"], name="idx_model_pricing_region"),
		]


class Customer(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	first_name = models.TextField()
	last_name = models.TextField()
	email = models.EmailField(blank=True, null=True)
	phone = models.TextField(blank=True, null=True)
	address_line1 = models.TextField(blank=True, null=True)
	address_line2 = models.TextField(blank=True, null=True)
	city = models.TextField(blank=True, null=True)
	state = models.TextField(blank=True, null=True)
	zip = models.TextField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "customers"

	def __str__(self):
		return f"{self.first_name} {self.last_name}".strip()


class Project(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	project_name = models.TextField()
	model = models.ForeignKey(ModelCatalog, on_delete=models.CASCADE, related_name="projects")
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="projects")
	region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="projects")
	sales_rep = models.ForeignKey(OpsUser, on_delete=models.CASCADE, related_name="sales_projects")
	pm = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_projects")
	rate_card_version = models.ForeignKey(RateCardVersion, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
	status = models.CharField(max_length=32, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
	site_address = models.TextField(blank=True, null=True)
	site_city = models.TextField(blank=True, null=True)
	site_state = models.TextField(blank=True, null=True)
	site_zip = models.TextField(blank=True, null=True)
	has_detached_structure = models.BooleanField(default=False)
	detached_structure_notes = models.TextField(blank=True, null=True)
	total_contract_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	total_true_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	bank_name = models.TextField(blank=True, null=True)
	contract_date = models.DateField(blank=True, null=True)
	est_start_date = models.DateField(blank=True, null=True)
	est_completion_date = models.DateField(blank=True, null=True)
	actual_completion_date = models.DateField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "projects"
		indexes = [
			models.Index(fields=["status"], name="idx_projects_status"),
			models.Index(fields=["region"], name="idx_projects_region"),
			models.Index(fields=["sales_rep"], name="idx_projects_sales"),
			models.Index(fields=["pm"], name="idx_projects_pm"),
			models.Index(fields=["model"], name="idx_projects_model"),
		]


class ProjectMetric(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="metrics")
	metric = models.ForeignKey(
		MetricDefinition,
		to_field="field_key",
		db_column="metric_key",
		on_delete=models.CASCADE,
		related_name="project_metrics",
	)
	value = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
	is_overridden = models.BooleanField(default=False)
	overridden_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="overridden_metrics")
	overridden_at = models.DateTimeField(blank=True, null=True)

	class Meta:
		db_table = "project_metrics"
		constraints = [
			models.UniqueConstraint(fields=["project", "metric"], name="project_metrics_project_metric_uniq"),
		]
		indexes = [
			models.Index(fields=["project"], name="idx_proj_metrics_project"),
		]


class ProjectMetricAudit(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="metric_audit")
	metric_key = models.TextField()
	old_value = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
	new_value = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
	changed_by = models.ForeignKey(OpsUser, on_delete=models.CASCADE, related_name="metric_changes")
	reason = models.TextField(blank=True, null=True)
	changed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_metric_audit"
		indexes = [
			models.Index(fields=["project"], name="idx_metric_audit_project"),
		]


class P10Order(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="p10_orders")
	order_number = models.TextField()
	order_date = models.DateField()
	customer_number = models.TextField(blank=True, null=True)
	subtotal = models.DecimalField(max_digits=12, decimal_places=2)
	freight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	sales_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	other_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	total = models.DecimalField(max_digits=12, decimal_places=2)
	amount_prepaid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	balance = models.DecimalField(max_digits=12, decimal_places=2)
	pdf_storage_key = models.TextField(blank=True, null=True)
	notes = models.TextField(blank=True, null=True)
	entered_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="entered_p10_orders")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "p10_orders"
		indexes = [
			models.Index(fields=["project"], name="idx_p10_project"),
		]


class ProjectExteriorPricing(models.Model):
	project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="exterior_pricing")
	base_sf = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	base_rate_per_sf = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	base_shell_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	total_customer_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_exterior_pricing"


class ProjectExteriorUpgrade(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="exterior_upgrades")
	line_order = models.IntegerField(default=0)
	description = models.TextField()
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.TextField(blank=True, null=True)
	rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	total = models.DecimalField(max_digits=12, decimal_places=2)
	edit_scope = models.CharField(max_length=16, choices=EditScope.choices, default=EditScope.UPGRADE)
	added_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="added_exterior_upgrades")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_exterior_upgrades"
		indexes = [
			models.Index(fields=["project"], name="idx_ext_upgrades_project"),
		]


class ProjectContractorBudget(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="contractor_budget")
	rate_key = models.TextField()
	label = models.TextField()
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.TextField(blank=True, null=True)
	rate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
	total = models.DecimalField(max_digits=12, decimal_places=2)
	trade_group = models.TextField()
	is_override = models.BooleanField(default=False)
	display_order = models.IntegerField(default=0)

	class Meta:
		db_table = "project_contractor_budget"
		constraints = [
			models.UniqueConstraint(fields=["project", "rate_key"], name="project_contractor_budget_project_key_uniq"),
		]
		indexes = [
			models.Index(fields=["project"], name="idx_contractor_budget_project"),
		]


class ProjectConcrete(models.Model):
	project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="concrete")
	total_concrete_cost = models.DecimalField(max_digits=12, decimal_places=2)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_concrete"


class ProjectConcreteLine(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="concrete_lines")
	line_order = models.IntegerField(default=0)
	description = models.TextField()
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.TextField(blank=True, null=True)
	rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	total = models.DecimalField(max_digits=12, decimal_places=2)
	notes = models.TextField(blank=True, null=True)

	class Meta:
		db_table = "project_concrete_lines"
		indexes = [
			models.Index(fields=["project"], name="idx_concrete_lines_project"),
		]


class ProjectInteriorContract(models.Model):
	project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="interior_contract")
	base_turnkey_amount = models.DecimalField(max_digits=12, decimal_places=2)
	regional_adder = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	adjusted_turnkey_amount = models.DecimalField(max_digits=12, decimal_places=2)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_interior_contract"


class ProjectCabinetContract(models.Model):
	project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="cabinet_contract")
	base_cabinet_amount = models.DecimalField(max_digits=12, decimal_places=2)
	total_cabinet_upgrades = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	total_countertop = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	total_cabinet_contract = models.DecimalField(max_digits=12, decimal_places=2)
	cabinet_pct_of_interior = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_cabinet_contract"


class ProjectCabinetUpgrade(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="cabinet_upgrades")
	category = models.TextField()
	line_order = models.IntegerField(default=0)
	description = models.TextField()
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.TextField(blank=True, null=True)
	rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	total = models.DecimalField(max_digits=12, decimal_places=2)
	edit_scope = models.CharField(max_length=16, choices=EditScope.choices, default=EditScope.UPGRADE)
	added_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="added_cabinet_upgrades")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_cabinet_upgrades"
		indexes = [
			models.Index(fields=["project"], name="idx_cab_upgrades_project"),
		]


class ProjectCountertopLine(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="countertop_lines")
	line_order = models.IntegerField(default=0)
	description = models.TextField()
	quantity_sf = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	rate_per_sf = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	total = models.DecimalField(max_digits=12, decimal_places=2)
	edit_scope = models.CharField(max_length=16, choices=EditScope.choices, default=EditScope.UPGRADE)
	added_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="added_countertop_lines")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_countertop_lines"
		indexes = [
			models.Index(fields=["project"], name="idx_countertop_project"),
		]


class ProjectInteriorUpgrade(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="interior_upgrades")
	category = models.TextField()
	line_order = models.IntegerField(default=0)
	description = models.TextField()
	quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
	customer_price = models.DecimalField(max_digits=12, decimal_places=2)
	true_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	edit_scope = models.CharField(max_length=16, choices=EditScope.choices, default=EditScope.UPGRADE)
	added_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="added_interior_upgrades")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_interior_upgrades"
		indexes = [
			models.Index(fields=["project"], name="idx_int_upgrades_project"),
		]


class ProjectContract(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="contracts")
	contract_number = models.TextField(blank=True, null=True)
	contract_date = models.DateField(blank=True, null=True)
	p10_material_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	concrete_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	exterior_labor_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	interior_turnkey_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	cabinet_contract_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	all_upgrades_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	total_contract_amount = models.DecimalField(max_digits=12, decimal_places=2)
	bank_name = models.TextField(blank=True, null=True)
	deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=2500)
	docusign_envelope_id = models.TextField(blank=True, null=True)
	docusign_status = models.TextField(blank=True, null=True)
	docusign_sent_at = models.DateTimeField(blank=True, null=True)
	docusign_signed_at = models.DateTimeField(blank=True, null=True)
	specification_notes = models.TextField(blank=True, null=True)
	contract_pdf_key = models.TextField(blank=True, null=True)
	version = models.IntegerField(default=1)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_contracts"
		indexes = [
			models.Index(fields=["project"], name="idx_contracts_project"),
		]


class ProjectDraw(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="draws")
	contract = models.ForeignKey(ProjectContract, on_delete=models.SET_NULL, null=True, blank=True, related_name="draws")
	draw_number = models.IntegerField()
	draw_label = models.TextField()
	draw_description = models.TextField(blank=True, null=True)
	calc_method = models.CharField(max_length=24, choices=DrawCalcMethod.choices)
	percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
	source_component = models.TextField(blank=True, null=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	is_detached_portion = models.BooleanField(default=False)
	detached_description = models.TextField(blank=True, null=True)
	detached_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	status = models.CharField(max_length=24, choices=DrawStatus.choices, default=DrawStatus.PENDING)
	phase_completed_at = models.DateTimeField(blank=True, null=True)
	phase_completed_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_draw_phases")
	qb_invoice_id = models.TextField(blank=True, null=True)
	qb_invoice_number = models.TextField(blank=True, null=True)
	date_invoiced = models.DateField(blank=True, null=True)
	date_due = models.DateField(blank=True, null=True)
	date_paid = models.DateField(blank=True, null=True)
	payment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
	display_order = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_draws"
		constraints = [
			models.UniqueConstraint(
				fields=["project", "draw_number", "is_detached_portion"],
				name="project_draws_project_number_detached_uniq",
			),
		]
		indexes = [
			models.Index(fields=["project"], name="idx_draws_project"),
			models.Index(fields=["status"], name="idx_draws_status"),
		]


class ChangeOrder(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="change_orders")
	contract = models.ForeignKey(ProjectContract, on_delete=models.SET_NULL, null=True, blank=True, related_name="change_orders")
	co_number = models.IntegerField()
	title = models.TextField()
	description = models.TextField(blank=True, null=True)
	amount_change = models.DecimalField(max_digits=12, decimal_places=2)
	new_contract_total = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(max_length=24, choices=ChangeOrderStatus.choices, default=ChangeOrderStatus.DRAFT)
	docusign_envelope_id = models.TextField(blank=True, null=True)
	docusign_signed_at = models.DateTimeField(blank=True, null=True)
	requested_by = models.ForeignKey(OpsUser, on_delete=models.CASCADE, related_name="requested_change_orders")
	approved_by = models.ForeignKey(OpsUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_change_orders")
	approved_at = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "change_orders"
		constraints = [
			models.UniqueConstraint(fields=["project", "co_number"], name="change_orders_project_number_uniq"),
		]
		indexes = [
			models.Index(fields=["project"], name="idx_change_orders_project"),
			models.Index(fields=["status"], name="idx_change_orders_status"),
		]


class ChangeOrderItem(models.Model):
	change_order = models.ForeignKey(ChangeOrder, on_delete=models.CASCADE, related_name="items")
	line_order = models.IntegerField(default=0)
	description = models.TextField()
	category = models.TextField()
	quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	unit = models.TextField(blank=True, null=True)
	rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	notes = models.TextField(blank=True, null=True)

	class Meta:
		db_table = "change_order_items"
		indexes = [
			models.Index(fields=["change_order"], name="idx_co_items_co"),
		]


class ProjectBudgetLine(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="budget_lines")
	trade_group = models.TextField()
	trade_label = models.TextField()
	budget_amount = models.DecimalField(max_digits=12, decimal_places=2)
	upgrade_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	total_budget = models.DecimalField(max_digits=12, decimal_places=2)
	actual_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	remaining = models.DecimalField(max_digits=12, decimal_places=2)
	display_order = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "project_budget_lines"
		constraints = [
			models.UniqueConstraint(fields=["project", "trade_group"], name="project_budget_lines_project_trade_uniq"),
		]
		indexes = [
			models.Index(fields=["project"], name="idx_budget_lines_project"),
		]


class ProjectBudgetActual(models.Model):
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="budget_actuals")
	budget_line = models.ForeignKey(ProjectBudgetLine, on_delete=models.CASCADE, related_name="actuals")
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	description = models.TextField(blank=True, null=True)
	invoice_reference = models.TextField(blank=True, null=True)
	date_entered = models.DateField(auto_now_add=True)
	entered_by = models.ForeignKey(OpsUser, on_delete=models.CASCADE, related_name="entered_actuals")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_budget_actuals"
		indexes = [
			models.Index(fields=["project"], name="idx_actuals_project"),
			models.Index(fields=["budget_line"], name="idx_actuals_budget_line"),
		]


class ContractEditLog(models.Model):
	id = models.BigAutoField(primary_key=True)
	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="edit_logs")
	table_name = models.TextField()
	record_id = models.IntegerField(blank=True, null=True)
	action = models.TextField()
	field_name = models.TextField(blank=True, null=True)
	old_value = models.TextField(blank=True, null=True)
	new_value = models.TextField(blank=True, null=True)
	edit_scope = models.CharField(max_length=16, choices=EditScope.choices)
	contract_status = models.CharField(max_length=32, choices=ContractStatus.choices)
	edited_by = models.ForeignKey(OpsUser, on_delete=models.CASCADE, related_name="contract_edits")
	user_role = models.CharField(max_length=32, choices=UserRole.choices)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "contract_edit_log"
		indexes = [
			models.Index(fields=["project"], name="idx_edit_log_project"),
			models.Index(fields=["created_at"], name="idx_edit_log_time"),
		]


class Notification(models.Model):
	id = models.BigAutoField(primary_key=True)
	recipient = models.ForeignKey(OpsUser, on_delete=models.CASCADE, related_name="notifications")
	project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
	type = models.TextField()
	title = models.TextField()
	message = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "notifications"
		indexes = [
			models.Index(fields=["recipient", "is_read"], name="idx_notifications_recipient"),
			models.Index(fields=["created_at"], name="idx_notifications_time"),
		]
