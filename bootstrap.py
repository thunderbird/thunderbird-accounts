import argparse
import shutil
from pathlib import Path

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


def copy_template(source, destination, from_scratch):
    source_path = Path(source)
    destination_path = Path(destination)

    if from_scratch:
        destination_path.unlink(missing_ok=True)
    if destination_path.is_file():
        return False

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source_path, destination_path)
    return True


def bootstrap_legacy(from_scratch):
    if copy_template('.env.example', '.env', from_scratch):
        print('\t* Copied .env.example to .env')  # noqa: T201

    data_path = Path('mail/stalwart_legacy/data')
    if data_path.is_dir() and from_scratch:
        shutil.rmtree(data_path)
        print(f'\t* Removed {data_path}')  # noqa: T201

    config_path = Path('mail/stalwart_legacy/etc/config.toml')
    if copy_template('config.toml.example', config_path, from_scratch):
        print(f'\t* Copied config.toml.example to {config_path}')  # noqa: T201


def bootstrap_new(from_scratch):
    config_path = Path('mail/stalwart/etc/config.json')
    if copy_template(config_path.with_name('config.json.example'), config_path, from_scratch):
        print(f'\t* Copied {config_path.with_name("config.json.example")} to {config_path}')  # noqa: T201

    print('Finished!')  # noqa: T201


def main():
    new_only = args.v016_only
    from_scratch = args.from_scratch

    print('Bootstrapping project:', args.__dict__)  # noqa: T201

    if not new_only:
        print('Bootstrapping v0.15')  # noqa: T201
        bootstrap_legacy(from_scratch)

    print('Bootstrapping v0.16')  # noqa: T201
    bootstrap_new(from_scratch)


if __name__ == '__main__':
    main()
