"""Runs the main() function of all other py files in this directory"""
import os
import importlib


def main():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    for curdir, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith('.py'):
                fullpath = os.path.join(curdir, f)
                mod_nm = '.'.join(fullpath[len(dir_path) + len(os.path.sep):-3].split(os.path.sep))
                if mod_nm == 'run_all':
                    continue
                print(f'Running {mod_nm}')
                mod = importlib.import_module(mod_nm)
                mod.main()


if __name__ == '__main__':
    main()
