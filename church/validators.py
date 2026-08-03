import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class StrongPasswordValidator:
    """
    Validates whether a password meets security requirements:
    - Minimum 8 characters long
    - Contains at least 1 uppercase letter
    - Contains at least 1 lowercase letter
    - Contains at least 1 numeric digit
    - Contains at least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    """
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Password must be at least %(min_length)d characters long."),
                code='password_too_short',
                params={'min_length': self.min_length},
            )
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter (A-Z)."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter (a-z)."),
                code='password_no_lower',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Password must contain at least one numeric digit (0-9)."),
                code='password_no_digit',
            )
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            raise ValidationError(
                _("Password must contain at least one special character (e.g. !@#$%^&*)."),
                code='password_no_symbol',
            )

    def get_help_text(self):
        return _(
            "Your password must be at least %(min_length)d characters long, "
            "and contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character." % {'min_length': self.min_length}
        )


def validate_phone_number(value):
    """Validates international or local contact numbers."""
    if not value:
        return
    cleaned = value.strip()
    pattern = r'^\+?[0-9\s\-\(\)]{7,20}$'
    if not re.match(pattern, cleaned):
        raise ValidationError(_("Enter a valid phone/contact number (7 to 20 digits)."))


def validate_email_address(value):
    """Validates email format."""
    if not value:
        return
    cleaned = value.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, cleaned):
        raise ValidationError(_("Enter a valid email address."))
