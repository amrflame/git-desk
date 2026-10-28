"""Build a local VSIX with the Python standard library (no npm install required)."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent
package = json.loads((ROOT / 'package.json').read_text())
NS = 'http://schemas.microsoft.com/developer/vsx-schema/2011'
ET.register_namespace('', NS)
def child(parent, name, attributes=None, text=None):
    node = ET.SubElement(parent, '{' + NS + '}' + name, attributes or {})
    node.text = text
    return node

manifest = ET.Element('{' + NS + '}PackageManifest', {'Version': '2.0.0'})
metadata = child(manifest, 'Metadata')
child(metadata, 'Identity', {'Language': 'en-US', 'Id': package['name'], 'Version': package['version'], 'Publisher': package['publisher']})
child(metadata, 'DisplayName', text=package['displayName'])
child(metadata, 'Description', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'}, package['description'])
child(metadata, 'Categories', text=','.join(package['categories']))
properties = child(metadata, 'Properties')
for name, value in {
    'Microsoft.VisualStudio.Code.Engine': package['engines']['vscode'],
    'Microsoft.VisualStudio.Code.ExtensionDependencies': ','.join(package['extensionDependencies']),
    'Microsoft.VisualStudio.Code.ExtensionPack': '',
    'Microsoft.VisualStudio.Code.ExtensionKind': 'workspace',
    'Microsoft.VisualStudio.Code.LocalizedLanguages': '',
    'Microsoft.VisualStudio.Code.EnabledApiProposals': '',
    'Microsoft.VisualStudio.Code.PreRelease': 'false',
    'Microsoft.VisualStudio.Code.ExecutesCode': 'true'
}.items():
    child(properties, 'Property', {'Id': name, 'Value': value})
installation = child(manifest, 'Installation')
child(installation, 'InstallationTarget', {'Id': 'Microsoft.VisualStudio.Code'})
child(manifest, 'Dependencies')
assets = child(manifest, 'Assets')
for asset, file in [('Microsoft.VisualStudio.Code.Manifest', 'package.json'), ('Microsoft.VisualStudio.Services.Content.Details', 'README.md'), ('Microsoft.VisualStudio.Services.Content.License', 'LICENSE')]:
    child(assets, 'Asset', {'Type': asset, 'Path': 'extension/' + file, 'Addressable': 'true'})
content_types = b'''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="json" ContentType="application/json"/>
<Default Extension="js" ContentType="application/javascript"/>
<Default Extension="md" ContentType="text/markdown"/>
<Default Extension="svg" ContentType="image/svg+xml"/>
<Default Extension="vsixmanifest" ContentType="text/xml"/>
<Override PartName="/extension/LICENSE" ContentType="text/plain"/>
</Types>'''
output = ROOT.parent / f"{package['name']}-{package['version']}.vsix"
with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
    archive.writestr('extension.vsixmanifest', ET.tostring(manifest, encoding='utf-8', xml_declaration=True))
    archive.writestr('[Content_Types].xml', content_types)
    for file in ['package.json', 'extension.js', 'README.md', 'LICENSE', 'media/git-desk.svg']:
        archive.write(ROOT / file, 'extension/' + file)
print(output)
