{% extends "mail_templated/base.tpl" %}

{% block subject %}Hello {{ user.username }}{% endblock %}

{% block body %}This is a plain text message.{% endblock %}

{% block html %}This is an <strong>html</strong> part.{% endblock %}