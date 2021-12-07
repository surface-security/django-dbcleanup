from django.db import models


class Note(models.Model):
    message = models.CharField(max_length=100)
    time = models.DateTimeField()


class Food(models.Model):
    name = models.CharField(max_length=100)
    last_eaten = models.DateTimeField()
    notes = models.ManyToManyField('Note')


class Bread(Food):
    crusty = models.BooleanField(default=True)


class FoodMonster(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    daily_quantity = models.IntegerField(default=1)
