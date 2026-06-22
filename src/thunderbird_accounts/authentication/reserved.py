from fnmatch import fnmatch
import re

# brand related names, and also help/support
brands = '(thunderbird|tbpro|thundermail|thunderbirdpro|mzla|mozilla|firefox)?'

# Brand names plus common tokens
names_with_brands = [
    brands + '?',
    brands + '[_|-]?admin?',
    brands + '[_|-]?support?',
    brands + '[_|-]?customer[_|-]?support?',
    brands + '[_|-]?help?',
    brands + '[_|-]?customer[_|-]?help?',
    brands + '[_|-]?mozilla?',
    brands + '[_|-]?email?',
    brands + '[_|-]?org?',
]
reserved_names = [n + '$' for n in names_with_brands]

# official/real versions
reserved_names = (
    reserved_names
    + ['official[_|-]?' + n for n in names_with_brands]
    + [n + '[_|-]?official$' for n in names_with_brands]
    + ['real[_|-]?' + n for n in names_with_brands]
    + [n + '[_|-]?real$' for n in names_with_brands]
)

# test users, match anything mzla-test* related
reserved_names += ['mzla-test[.]*']

# common example usernames
reserved_names += ['user(name|[_|-]name)*$'] + ['example(user|[_|-]user|name|[_|-]name)*$'] + ['^test$']

# potential company team use
teams = [
    'team(s)*',
    'hr',
    'accounts',
    'engineering',
    'marketing',
    'design',
    'legal',
    'privacy',
    'policy',
    'finance',
    'sales',
]
reserved_names += ['^' + n + '(team|_team)*$' for n in teams] + ['contact(us|[_|-]us)*$']

# servers and internal teams
servers = [
    'admin',
    'administrator',
    'anonymous',
    'billing',
    'bounce',
    'email',
    'hostmaster',
    'imap',
    'info',
    'is',
    'it',
    'mailer',
    'mailerdaemon',
    'mailer-daemon',
    'mis',
    'news',
    'nobody',
    'noc',
    'noreply',
    'no-reply',
    'pop',
    'pop3',
    'postmaster',
    'root',
    'security',
    'smtp',
    'ssl',
    'ssladmin',
    'ssladministrator',
    'sslwebmaster',
    'superuser',
    'sysadmin',
    'sysadministrator',
    'usernet',
    'uucp',
    'ftp',
    'sftp',
    'webmaster',
    'www',
]
support = ['support', 'help', 'abuse', 'terms']
reserved_names += ['^' + n + '$' for n in (servers + support)]


# birbs
reserved_names += ['roc$', 'ezio$', 'mithu$', 'ava$', 'callum$', 'sora$', 'robin$', 'nemo$']

regexes = [re.compile('^' + n) for n in reserved_names]


def is_reserved(test_string: str) -> bool:
    """Checks the address or random string is a reserved name which should fail user or alias creation if so."""
    from thunderbird_accounts.authentication.models import UsernameBlockListEntry

    matches = any(r.match(test_string) for r in regexes)
    if matches:
        return True

    # This most likely won't scale well in the future...
    entries = UsernameBlockListEntry.objects.all()

    # This is a filename search, but it's simpler than regex so hopefully it won't be a footgun. :)
    # https://docs.python.org/3/library/fnmatch.html#fnmatch.fnmatch
    return any(fnmatch(test_string, entry.pattern) for entry in entries)
