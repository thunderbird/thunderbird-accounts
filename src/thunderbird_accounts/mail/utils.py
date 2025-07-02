from django.contrib.auth.hashers import make_password, identify_hasher


def save_app_password(label, password):
    """Hashes a given password, formats it with the label and saves it to the secret field."""
    hashed_password = make_password(password, hasher='argon2')
    hash_algo = identify_hasher(hashed_password)

    # We need to strip out the leading argon2$ from the hashed value
    if hash_algo.algorithm == 'argon2':
        _, hashed_password = hashed_password.split('argon2$')
        # Note: This is an intentional $, not a failed javascript template literal
        hashed_password = f'${hashed_password}'
    else:
        return None

    secret_string = f'$app${label}${hashed_password}'
    return secret_string
