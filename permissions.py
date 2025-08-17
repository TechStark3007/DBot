import discord
from functools import wraps


# ROLE CHECK
def role_only(*allowed_roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            user_roles = [role.name for role in interaction.user.roles]
            if not any(r in user_roles for r in allowed_roles):
                return  # Command is ignored if the user has no defined role
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

def can_control(interaction_user, requester, allowed_roles):
    user_roles = [role.name for role in interaction_user.roles]
    return (
        interaction_user == requester
        or any(r in user_roles for r in allowed_roles)
    )


def disable_buttons_if_not_allowed(view, can_control):
    if not can_control:
        for item in view.children:
            if hasattr(item, "disabled"):
                item.disabled = True



