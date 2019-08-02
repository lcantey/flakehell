import ast
import re
from importlib import import_module
from pathlib import Path


REX_CODE = re.compile(r'^[A-Z]{1,5}[0-9]{1,5}$')


class CollectStrings(ast.NodeVisitor):
    _strings = []

    def visit_Str(self, node):
        self._strings.append(node.s)


def get_messages(code, content):
    root = ast.parse(content)
    collector = CollectStrings()
    collector.visit(root)

    messages = dict()
    for message in collector._strings:
        message_code, _, message_text = message.partition(' ')
        if not message_text:
            continue
        if not REX_CODE.match(message_code):
            continue
        if code and not message_code.startswith(code):
            continue
        messages[message_code] = message_text
    return messages


def extract_default(name):
    module = import_module(name)
    content = Path(module.__file__).read_text()
    return get_messages(code='', content=content)


def extract(name):
    name = name.replace('-', '_')
    function_name = 'extract_' + name

    # use ad-hoc extractor if available
    if function_name in globals():
        return globals()[function_name]()

    # try to extract by default algorithm
    return extract_default(name)


# AD-HOC EXTRACTORS


def extract_flake8_commas():
    from flake8_commas._base import ERRORS

    return dict(ERRORS.values())


def extract_flake8_quotes():
    import flake8_quotes

    content = Path(flake8_quotes.__file__).read_text()
    return get_messages(code='Q0', content=content)


def extract_flake8_variables_names():
    from flake8_variables_names import checker

    content = Path(checker.__file__).read_text()
    return get_messages(code='VNE', content=content)


def extract_logging_format():
    from logging_format import violations

    content = Path(violations.__file__).read_text()
    return get_messages(code='G', content=content)


def extract_flake8_debugger():
    from flake8_debugger import DEBUGGER_ERROR_CODE
    return {DEBUGGER_ERROR_CODE: 'trace found'}


def extract_flake_mutable():
    from mutable_defaults import MutableDefaultChecker

    return {MutableDefaultChecker._code: MutableDefaultChecker._error_tmpl}


def extract_pep8ext_naming():
    import pep8ext_naming

    codes = dict()
    for checker_name in dir(pep8ext_naming):
        if not checker_name.endswith('Check'):
            continue
        checker = getattr(pep8ext_naming, checker_name)
        for code, message in checker.__dict__.items():
            if code[0] == 'N':
                codes[code] = message
    return codes


def extract_flake8_alfred():
    return {'B1': 'banned symbol'}


def extract_flake8_eradicate():
    return {'E800': 'Found commented out code: {0}'}


def extract_flake8_annotations_complexity():
    from flake8_annotations_complexity.checker import AnnotationsComplexityChecker

    code, message = AnnotationsComplexityChecker._error_message_template.split(' ', maxsplit=1)
    return {code: message}


def extract_flake8_string_format():
    from flake8_string_format import StringFormatChecker

    return {'P{}'.format(c): m for c, m in StringFormatChecker.ERRORS.items()}


def extract_flake8_broken_line():
    from flake8_broken_line import N400

    code, message = N400.split(': ')
    return {code: message}


def extract_flake8_bandit():
    from bandit.core.extension_loader import MANAGER

    codes = dict()
    for blacklist in MANAGER.blacklist.values():
        for check in blacklist:
            codes[check['id']] = check['message']
    for plugin in MANAGER.plugins:
        codes[plugin.plugin._test_id] = plugin.name.replace('_', ' ')
    return codes


def extract_pylint():
    import pylint.checkers

    codes = dict()
    for path in Path(pylint.checkers.__path__[0]).iterdir():
        module = import_module('pylint.checkers.' + path.stem)
        for class_name in dir(module):
            cls = getattr(module, class_name, None)
            msgs = getattr(cls, 'msgs', None)
            if not msgs:
                continue
            codes.update({code: msg.replace('\n', ' ') for code, (msg, *_) in msgs.items()})
    return codes


def extract_pyflakes():
    from flake8.plugins.pyflakes import FLAKE8_PYFLAKES_CODES
    from pyflakes import messages

    codes = dict()
    for class_name, code in FLAKE8_PYFLAKES_CODES.items():
        codes[code] = getattr(messages, class_name).message
    return codes


def extract_flake8_rst_docstrings():
    from flake8_rst_docstrings import code_mappings_by_level

    codes = dict()
    for level, codes_mapping in code_mappings_by_level.items():
        for message, number in codes_mapping.items():
            code = 'RST{}{:02d}'.format(level, number)
            codes[code] = message
    return codes


def extract_wemake_python_styleguide():
    from wemake_python_styleguide.violations import best_practices, complexity, consistency, naming

    codes = dict()
    for module in (best_practices, complexity, consistency, naming):
        for checker_name in dir(module):
            if not checker_name.endswith('Violation'):
                continue
            checker = getattr(module, checker_name)
            if not hasattr(checker, 'code'):
                continue
            code = 'WPS' + str(checker.code).zfill(3)
            codes[code] = checker.error_template
        return codes