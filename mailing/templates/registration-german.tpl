{% extends "mail_templated/base.tpl" %}

{% block subject %}Willkommen bei Kanbon{% endblock %}

{% block body %}Hallo {{ user.first_name }}!

vielen Dank für deine Registrierung bei Kanbon.
Um zu bestätigen, dass du Zugriff auf diese E-Mail Adresse hast, klicke bitte auf folgenden Link oder kopiere ihn in deine Addresszeile:

https://www.kanbon.at/v/{{ email }}/{{ token_1 }}{{ token_2 }}

Du wirst in deinem E-Mail Postfach gelegentlich über wichtige Nachrichten zu deinem Account informiert.
Weiters kannst Du dein Passwort mit deiner E-Mail Adresse zurücksetzen, solltest Du es mal vergessen.{% endblock %}

{% block html %}<style>
    .button {
        border-radius: 2px;
    }

    .button a {
        padding: 8px 12px;
        border: 1px solid #E87405;
        border-radius: 2px;
        font-family: Helvetica, Arial, sans-serif;
        font-size: 14px;
        color: #ffffff;
        text-decoration: none;
        font-weight: bold;
        display: inline-block;
}

</style>

Hallo {{ user.first_name }}!
<p>vielen Dank für deine Registrierung bei Kanbon.</p>
<p>Um zu bestätigen, dass du Zugriff auf diese E-Mail Adresse hast, gib bitte folgenden Zahlencode an:</p>

<table width="100%" cellspacing="0" cellpadding="0">
    <tr>
        <td>
            <table cellspacing="0" cellpadding="0">
                <tr>
                    <td>
                        <h2>{{ token_1 }}-{{ token_2 }}</h2>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>

<p>Alternativ kannst du zur Bestätigung auch folgenden Link verwenden:</p>

<table width="100%" cellspacing="0" cellpadding="0">
    <tr>
        <td>
            <table cellspacing="0" cellpadding="0">
                <tr>
                    <td class="button" bgcolor="#E87405">
                        <a class="link" href="https://www.kanbon.at/v/{{ email }}/{{ token_1 }}{{ token_2 }}">E-Mail Adresse bestätigen</a>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
</table>

<p>Du wirst in deinem E-Mail Postfach gelegentlich über wichtige Nachrichten zu deinem Account informiert.<br>
Weiters kannst Du dein Passwort mit deiner E-Mail Adresse zurücksetzen, solltest Du es mal vergessen.</p>

<p>Mit freundlichen Grüßen<br>
Dein Kanbon Team</p>{% endblock %}