from pathlib import Path
import argparse
import os
import shutil
from shutil import SameFileError

arg_parse = argparse.ArgumentParser()

arg_parse.add_argument(
    '--from-scratch',
    action='store_true',
    help='deletes any existing configs. WARNING: Make sure to backup your local env, and stalwart configs!',
)
arg_parse.add_argument(
    '--v016-only',
    action='store_true',
    help='Only bootstraps Stalwart v0.16 / Stalwart New',
)

args = arg_parse.parse_args()


def bootstrap_legacy(from_scratch):
    if not os.path.isfile('.env') or from_scratch:
        try:
            shutil.copy('.env.example', '.env')
            print('\t* Copied .env.example to .env')  # noqa: T201
        except SameFileError:
            pass

    if os.path.isdir('mail/stalwart_legacy/data') and from_scratch:
        shutil.rmtree('mail/stalwart_legacy/data')
        print('\t* Removed mail/stalwart_legacy/data')  # noqa: T201

    if not os.path.isfile('mail/stalwart_legacy/etc/config.toml') or from_scratch:
        try:
            os.makedirs('mail/stalwart_legacy/etc/', exist_ok=True)
            shutil.copy('config.toml.example', 'mail/stalwart_legacy/etc/config.toml')
            print('\t* Copied config.toml.example to mail/stalwart_legacy/etc/config.toml')  # noqa: T201
        except SameFileError:
            pass


def bootstrap_new(from_scratch):
    # Handle v0.16
    path = Path('mail/stalwart/lib')
    if os.path.isdir(path) and from_scratch:
        os.remove(path / 'main.db')
        print(f'\t* Removed {path}/main.db')  # noqa: T201
    if not os.path.isfile(path / 'main.db'):
        shutil.copy(path / 'main.db.example', path / 'main.db')
        print(f'\t* Copied {path}/main.db.example to {path}/main.db')  # noqa: T201

    path = Path('mail/stalwart/etc')
    if os.path.isdir(path) and from_scratch:
        os.remove(path / 'config.json')
        print(f'\t* Removed {path}/config.json')  # noqa: T201
    if not os.path.isfile(path / 'config.json'):
        shutil.copy(path / 'config.json.example', path / 'config.json')
        print(f'\t* Copied {path}/config.json.example to {path}/config.json')  # noqa: T201

    print('Finished!')  # noqa: T201


def main():
    new_only = args.v016_only
    from_scratch = args.from_scratch

    print('Bootstrapping project:', args.__dict__)  # noqa: T201

    if not new_only:
        print('Bootstrapping v0.15') # noqa: T201
        bootstrap_legacy(from_scratch)

    print('Bootstrapping v0.16') # noqa: T201
    bootstrap_new(from_scratch)


if __name__ == '__main__':
    main()
