import re

# brand related names, and also help/support
brands = "(thunderbird|thunderbirdpro|mzla|mozilla|firefox)?"

# Brand names plus common tokens
names_with_brands = [
    brands + "?",
    brands + "[_|-]?support?",
    brands + "[_|-]?customer[_|-]?support?",
    brands + "[_|-]?help?",
    brands + "[_|-]?customer[_|-]?help?",
    brands + "[_|-]?mozilla?",
    brands + "[_|-]?email?",
    brands + "[_|-]?org?"
]
reserved_names = [n + "$" for n in names_with_brands]

# official/real versions
reserved_names = reserved_names + [
        'official[_|-]?' + n for n in names_with_brands
    ] + [
        n + '[_|-]?official$' for n in names_with_brands
    ] + [
        'real[_|-]?' + n for n in names_with_brands
    ] + [
        n + '[_|-]?real$' for n in names_with_brands
    ]

# test users, match anything mzla-test* related
reserved_names += ["mzla-test[.]*"]

# common example usernames
reserved_names += ["user(name|[_|-]name)*$"] + ["example(user|[_|-]user|name|[_|-]name)*$"] + ["^test$"]

# potential company team use
team_suffix = "(team|_team)*$"
reserved_names += ["team$"] + ["hr$"] + ["accounts" + team_suffix] + ["engineering" + team_suffix] \
    + ["marketing" + team_suffix] + ["design" + team_suffix] + ["contact(us|[_|-]us)*$"]

# mailserver and support
reserved_names += ["^root$", "^postmaster$", "^hostmaster$", "^support$", "^help$", "^abuse$"]

# birbs
reserved_names += ["roc$", "ezio$", "mithu$", "ava$", "callum$", "sora$", "robin$", "nemo$"]

regexes = [re.compile("^" + n) for n in reserved_names]

def is_reserved(testString):
    return any(r.match(testString) for r in regexes)
