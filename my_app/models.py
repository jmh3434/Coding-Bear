from django.db import models
from django.db.models.aggregates import Count
from random import randint
from datetime import datetime   



import re
import bcrypt
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
class UserManager(models.Manager):
    def validate(self, form):
        errors = {}
        if len(form['first_name']) < 2:
            errors['first_name'] = 'First Name must be at least 2 characters'

        if len(form['last_name']) < 2:
            errors['last_name'] = 'Last Name must be at least 2 characters'

        if not EMAIL_REGEX.match(form['email']):
            errors['email'] = 'Invalid Email Address'
        
        email_check = self.filter(email=form['email'])
        if email_check:
            errors['email'] = "Email already in use"

        if len(form['password']) < 8:
            errors['password'] = 'Password must be at least 8 characters'
        
        if form['password'] != form['confirm']:
            errors['password'] = 'Passwords do not match'
        
        return errors
    
    def authenticate(self, email, password):
        users = self.filter(email=email)
        if not users:
            return False

        user = users[0]
        return bcrypt.checkpw(password.encode(), user.password.encode())

    def register(self, form):
        pw = bcrypt.hashpw(form['password'].encode(), bcrypt.gensalt()).decode()
        return self.create(
            first_name = form['first_name'],
            last_name = form['last_name'],
            email = form['email'],
            password = pw,
        )

class QuoteManager(models.Manager):
    def random(self):
        count = self.aggregate(count=Count('id'))['count']
        random_index = randint(0, count - 1)
        return self.all()[random_index]
    def validate(self, form):
        errors = {}
        if len(form['quote']) < 2:
            errors['quote'] = 'Quote must be at least 2 characters'

        return errors

class MovieManager(models.Manager):
    def validate(self, form):
        errors = {}
        if len(form['title']) < 2:
            errors['quote'] = 'Title must be at least 2 characters'
        if len(form['image']) < 1:
            errors['image'] = 'Add an image for the new movie!'

        return errors

# Create your models here.
class User(models.Model):
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    image_url = models.CharField(max_length=255,null=True)
    high_score = models.IntegerField(default=0,null=True)
    objects = UserManager()
    #user_quotes
    #user_movies
    #liked_quotes

class Movie(models.Model):
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=255)
    image_url = models.CharField(max_length=255,null=True)
    poster = models.ForeignKey(User, related_name='user_movies', on_delete=models.CASCADE)
    objects = MovieManager()
    # movie_quotes
class Quote(models.Model):
    quote = models.CharField(max_length=255)
    poster = models.ForeignKey(User, related_name='user_quotes', on_delete=models.CASCADE)
    user_likes = models.ManyToManyField(User, related_name='liked_quotes',through='UserQuote')
    movie = models.ForeignKey(Movie, related_name="movie_quotes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = QuoteManager()

class Comment(models.Model):
    comment = models.CharField(max_length=255)
    poster = models.ForeignKey(User, related_name='user_comments', on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, related_name="quote_comments", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class UserQuote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

# Users have quotes which have movies
# Users have wall_message which have post_comments
