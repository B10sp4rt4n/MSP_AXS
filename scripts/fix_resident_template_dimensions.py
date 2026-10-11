"""Normalize optional OOXML dimensions without changing template cells/styles."""
from pathlib import Path
from zipfile import ZipFile


def main():
    path = Path(__file__).resolve().parents[1] / 'backend/static/plantilla_residentes.xlsx'
    with ZipFile(path) as source:
        entries = [(entry, source.read(entry.filename)) for entry in source.infolist()]
    temporary = path.with_suffix('.tmp')
    with ZipFile(temporary, 'w') as target:
        for entry, data in entries:
            if entry.filename == 'xl/worksheets/sheet1.xml' and b'<x:dimension ' not in data:
                data = data.replace(b'<x:sheetViews>', b'<x:dimension ref="A1:D501"/><x:sheetViews>', 1)
            target.writestr(entry, data)
    temporary.replace(path)


if __name__ == '__main__':
    main()
