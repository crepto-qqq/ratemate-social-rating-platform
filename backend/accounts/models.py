# accounts/models.py
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class User_profile(models.Model):
    id = models.BigAutoField(primary_key=True)
    userName = models.CharField(max_length=30, unique=False,null=False, verbose_name="用户名")
    email = models.EmailField(unique=True, verbose_name="注册邮箱")
    password = models.CharField(max_length=128, verbose_name="密码")
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        verbose_name="头像",
    )
    bio = models.TextField(blank=True, verbose_name="简介")

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.email
