"""Bundle trusted unnamed-package Java sources for JDK source-launcher execution."""
import re


def bundle_java_sources(main,sources):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*',main) or main not in sources:raise RuntimeError('Invalid Java source main identifier')
    ordered=[main,*sorted(name for name in sources if name!=main)];imports=[];bodies=[]
    for name in ordered:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*',name):raise RuntimeError('Invalid dependency identifier')
        text=sources[name]
        if re.search(r'(?m)^\s*package\s',text):raise RuntimeError('Only trusted unnamed-package source bundles are supported')
        declaration=rf'(?m)^public class {re.escape(name)}\b'
        if len(re.findall(declaration,text))!=1:raise RuntimeError('Source must declare its exact public top-level class once')
        imports.extend(re.findall(r'(?m)^import [^;\r\n]+;',text))
        body=re.sub(r'(?m)^import [^;\r\n]+;\s*','',text)
        if name!=main:body=re.sub(declaration,'class '+name,body,count=1)
        bodies.append(body.strip())
    result='\n'.join(dict.fromkeys(imports))+'\n\n'+'\n\n'.join(bodies)+'\n'
    if re.findall(r'(?m)^public class (\w+)',result)!=[main]:raise RuntimeError('Unexpected public class in bundle')
    return result
