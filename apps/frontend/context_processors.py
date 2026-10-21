

def user_context(request):
    """Makes user role and company available to all templates."""
    if not request.user.is_authenticated:
        return {}
    membership = getattr(request.user, 'membership', None)
    return {
        'user_role': membership.get_role_display() if membership else 'Administrator',
        'user_company': membership.company if membership else None,
    }