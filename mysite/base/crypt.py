#!/usr/bin/env python
# -*- coding:utf-8 -*-
from django.utils.encoding import smart_str


def encryption(s, key=101):
    if not s:
        return ''
    s = s.strip()
    b = bytearray(str(s).encode("utf-8"))
    n = len(b)
    c = bytearray(n * 2)
    j = 0
    for i in range(0, n):
        b1 = b[i]
        b2 = b1 ^ key  # b1 = b2^ key
        c1 = b2 % 16
        c2 = b2 // 16  # b2= c2*16 + c1
        c1 = c1 + 65
        c2 = c2 + 65
        c[j] = c1
        c[j + 1] = c2
        j = j + 2
    return c.decode("utf-8")


def decryption(s, key=101):
    if not s:
        return ''
    s = s.strip()
    c = bytearray(str(s).encode("utf-8"))
    n = len(c)
    if n % 2 != 0:
        return None
    n = n // 2
    b = bytearray(n)
    j = 0
    for i in range(0, n):
        c1 = c[j]
        c2 = c[j + 1]
        j = j + 2
        c1 = c1 - 65
        c2 = c2 - 65
        b2 = c2 * 16 + c1
        b1 = b2 ^ key
        b[i] = b1
    try:
        return b.decode("utf-8")
    except:
        return None
