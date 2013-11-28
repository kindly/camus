from flask import Flask, request, render_template

def content(path=None):
    return render_template("core/index.html")

def manage(path=None):
    return render_template("core/base.html")
