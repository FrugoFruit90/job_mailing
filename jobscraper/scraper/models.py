from django.db import models

class HypeStatus(models.IntegerChoices):
    UNKNOWN = 0  # special case
    FUCK_IT = 1
    INTERESTED = 2
    HYPED = 3

class JobBoard(models.IntegerChoices):
    NO_FLUFF = 1
    JUST_JOIN_IT = 2
    PRACUJ = 3

class CompanyManager(models.Manager):
    def get_possible_match(self, name: str) -> models.QuerySet:
        """There are different company names on different boards."""
        # TODO: matching by company url
        # TODO: non-polish: gmbh, llc
        stripped_name = name.replace('sp. z o.o.', '').strip()
        # if name didn't have sp. z o.o., let's add it to the check
        name_with_sp = f'{stripped_name} sp. z o.o.'
        return (
            self.filter(name__iexact=stripped_name)
            | self.filter(name__iexact=name_with_sp)
        )
        
    def create_or_update_if_better(
        self,
        name: str,
        url: str,
        **kwargs,
    ):
        url = url.strip()
        possible_matches = self.get_possible_match(name)
        if possible_matches.count() == 1:
            # if we have only one possible match, let's update it
            company = possible_matches.first()
            # Update company if needed
            if company.url != url:
                company.url = url
                company.save(update_fields=['url'])
            return company
        # if 0 or more than 1 possible matches, we create a new company
        # if there's more than 1, we can't be sure that this is the same one,
        # so we create a new company
        return self.create(
            name=name.replace('sp. z o.o.', '').strip(),
            url=url,
            **kwargs,
        )

class Company(models.Model):
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255, blank=True)
    size_from = models.IntegerField(default=0)
    size_to = models.IntegerField(default=0)
    url = models.CharField(max_length=1024, blank=True)
    status = models.IntegerField(choices=HypeStatus.choices, default=HypeStatus.UNKNOWN)
    
    objects = CompanyManager()

    def __str__(self) -> str:
        return self.name
        
    class Meta:
        db_table = 'grabbo_company'  # Use existing table

class Job(models.Model):
    board = models.IntegerField(choices=JobBoard.choices)
    original_id = models.CharField(max_length=256)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=256)
    url = models.CharField(max_length=256)
    seniority = models.CharField(max_length=256, blank=True)
    salary_text = models.CharField(max_length=256, blank=True)
    status = models.IntegerField(choices=HypeStatus.choices, default=HypeStatus.UNKNOWN)
    created_at = models.DateTimeField(auto_now_add=True)
    lena_comparibility = models.FloatField(default=0.0)
    # Adding fields that are required in the database but were missing in your model
    description = models.TextField(null=True, blank=True)  # Required field
    # Add any other missing fields here

    def __str__(self) -> str:
        return f'{self.title} in {self.company}'
        
    class Meta:
        db_table = 'grabbo_job'  # Use existing table
