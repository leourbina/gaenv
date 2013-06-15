#
from distutils.sysconfig import get_python_lib
import os
import inspect
import argparse
import re

sys_path_build = """# Auto generated by gaenv
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))"""


def main():
    parser = argparse.ArgumentParser(description='Command line utility for managing appengine thirdparty packages')
    parser.add_argument('--requirements', type=str, default='requirements.txt',
                        help='specify the requirements file default(requirements.txt)')
    parser.add_argument('--lib', type=str, default='gaenv_lib',
                        help='change the output dir, default is gaenv_lib')
    args = parser.parse_args()

    # Build requirements path & check for existence
    current_path = os.getcwd()
    requirement_path = os.path.join(current_path, args.requirements)
    if not os.path.exists(requirement_path):
        print 'requirements file %s not found' % requirement_path
        exit(0)

    requirements = []
    with open(requirement_path, 'r') as file:
        for requirement in file:
            req = re.split('([<>=]*)', requirement.strip())
            if req:
                requirements.append(req)

    package_path = get_python_lib()
    links = []
    # Find python packages on current python binary
    for package in os.listdir(package_path):
        if package.lower().endswith('.egg-info'):
            parts = package.split('-')
            for req in requirements:
                if req[0].lower() == parts[0].lower():
                    if len(req) == 1 or len(req) == 3 and eval('"%s" %s "%s"' % (parts[1], req[1], req[2])):
                        source = os.path.join(package_path, package, 'top_level.txt')
                        if os.path.exists(source):
                            links.extend(open(source, 'r').readlines())

    # Now we create the links
    if links:
        libs = os.path.join(current_path, args.lib)
        if not os.path.exists(libs):
            os.makedirs(libs)

        with open(os.path.join(libs, '__init__.py'), 'wb') as f:
            f.write(sys_path_build)

        for link in links:
            link = link.strip()
            symlink = os.path.join(package_path, link)
            if not os.path.exists(symlink) and os.path.exists(symlink + '.py'):
                symlink += '.py'
                dest = os.path.join(libs, link + '.py')
            else:
                dest = os.path.join(libs, link)

            if os.path.exists(symlink) and not os.path.exists(dest):
                os.symlink(symlink, dest)

            print 'Found and linked: %s' % link

        print 'Note that this can damage your python source, make sure you have appropriate precaution for undoing.'
        add_import = raw_input('Do you want to auto detect and insert imports? [yN]:').lower()
        if add_import == 'y':
            yaml_file = os.path.join(current_path, 'app.yaml')
            if not os.path.exists(yaml_file):
                print 'No app.yaml found'
            else:
                replace = []
                # Find entry point scripts base on app.yaml
                with open(yaml_file, 'r') as f:
                    for line in f:
                        if 'script:' in line:
                            detect = line.strip().split(' ').pop().split('.')
                            detect.pop()
                            possible_path = os.path.join(current_path, *detect)
                            if os.path.isfile(possible_path + '.py'):
                                replace.append(possible_path + '.py')
                            elif os.path.isdir(possible_path) and \
                                    os.path.isfile(os.path.join(possible_path, '__init__.py')):
                                replace.append(os.path.join(possible_path, '__init__.py'))

                if replace:
                    # Replace if there is no import
                    import_statement = 'import %s' % args.lib
                    for r in replace:
                        with open(r, 'r') as f:
                            source_code = f.read()
                        if import_statement not in source_code:
                            with open(r, 'wb') as f:
                                f.write(source_code.replace('import', import_statement + '\nimport', 1))
                                print 'added [%s] in [%s]' % (import_statement, r)
                        else:
                            print 'already exists in [%s] skipping' % r

        print 'Done, make sure you have import %s, on your script handlers.' % args.lib