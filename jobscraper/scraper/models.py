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

class Company(models.Model):
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255, blank=True)
    size_from = models.IntegerField(default=0)
    size_to = models.IntegerField(default=0)
    url = models.CharField(max_length=1024, blank=True)
    status = models.IntegerField(choices=HypeStatus.choices, default=HypeStatus.UNKNOWN)

    def __str__(self) -> str:
        return self.name
        
    class Meta:
        db_table = 'grabbo_company'  # Use existing table
        unique_together = ['name'] 

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

    def __str__(self) -> str:
        return f'{self.title} in {self.company}'
        
    class Meta:
        db_table = 'grabbo_job'  # Use existing table
