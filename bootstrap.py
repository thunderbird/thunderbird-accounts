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

args = arg_parse.parse_args()


def main():
    from_scratch = args.from_scratch

    new_env = False

    print('Bootstrapping project:')
    if not os.path.isfile('.env') or from_scratch:
        try:
            shutil.copy('.env.example', '.env')
            print('\t* Copied .env.example to .env')
            new_env = True
        except SameFileError:
            pass

    if os.path.isdir('mail/data') and from_scratch:
        shutil.rmtree('mail/data')
        print('\t* Removed mail/data')

    if not os.path.isfile('mail/etc/config.toml') or from_scratch:
        try:
            shutil.copy('.env.example', '.env')
            print('\t* Copied config.toml.example to mail/etc/config.toml')
        except SameFileError:
            pass

    print('\n')
    if new_env:
        print('Please boot up docker-compose.yml in another window...')
        input('Press any key when docker is booted!')

        print('Creating an api key')
        os.system('./manage.py create_stalwart_api_key')

        print('Please restart docker before developing')

    print('Finished!')


if __name__ == '__main__':
    main()
