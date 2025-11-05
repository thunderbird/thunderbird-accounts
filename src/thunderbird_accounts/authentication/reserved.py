import re

# brand related names, and also help/support
brands = "(thunderbird|thunderbirdpro|mzla|mozilla|firefox|help|support)"

# Brand names plus common tokens
names_with_brands = [
    brands + "+",
    brands + ".*support+",
    brands + ".*help+",
    brands + ".*mozilla+",
    brands + ".*email+",
    brands + ".*org+"
]
reserved_names = [n + "$" for n in names_with_brands]

# official/real versions
reserved_names = reserved_names + [
        'official[_]*' + n for n in names_with_brands
    ] + [
        n + '[_]*official$' for n in names_with_brands
    ] + [
        'real[_]*' + n for n in names_with_brands
    ] + [
        n + '[_]*real$' for n in names_with_brands
    ]

# test users, match anything mzla-test* related
reserved_names += ["mzla-test[.]*"]

# common example usernames
reserved_names += ["user(name|_name)*$"] + ["example(user|_user|name|_name)*$"] + ["test$"]

# potential company team use
team_suffix = "(team|_team)*$"
reserved_names += ["team$"] + ["hr$"] + ["accounts" + team_suffix] + ["engineering" + team_suffix] \
    + ["marketing" + team_suffix] + ["design" + team_suffix] + ["contact(us|_us)*$"]

# mailserver general
reserved_names += ["root$", "postmaster$", "hostmaster$"]

# birbs
reserved_names += ["roc$", "ezio$", "mithu$", "ava$", "callum$", "sora$", "robin$", "nemo$"]

regexes = [re.compile("^" + n) for n in reserved_names]

def is_reserved(testString):
    return any(r.match(testString) for r in regexes)
