import win32com.client
import winreg
import sys
import codecs

# Force UTF-8 output
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

print("=" * 60)
print("CHECKING AVAILABLE OLE DB PROVIDERS")
print("=" * 60)

# Try common OLE DB providers
providers_to_test = [
    ('SQLOLEDB', 'SQL Server'),
    ('MSOLAP', 'Analysis Services'),
    ('MSOLAP.8', 'Analysis Services 2012+'),
    ('MSOLAP.9', 'Analysis Services 2016+'),
    ('MSDASQL', 'ODBC'),
    ('Microsoft.ACE.OLEDB.12.0', 'Access/Excel 2007'),
    ('Microsoft.ACE.OLEDB.16.0', 'Access/Excel 2016'),
    ('Microsoft.ACE.OLEDB.17.0', 'Access/Excel 2019'),
]

found_providers = []

for prov, desc in providers_to_test:
    try:
        cat = win32com.client.Dispatch('ADODB.Connection')
        try:
            cat.Provider = prov
            # Just test that provider exists, don't actually connect
            print(f"[OK] {prov} - {desc}")
            found_providers.append((prov, desc))
        except:
            pass
        try:
            cat.Close()
        except:
            pass
    except Exception as e:
        pass

print(f"\nFound {len(found_providers)} providers")

# Check registry for MSOLAP specifically
print("\n" + "=" * 60)
print("CHECKING REGISTRY FOR MSOLAP")
print("=" * 60)

try:
    key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'CLSID')
    i = 0
    msolap_list = []
    while i < 2000:
        try:
            clsid = winreg.EnumKey(key, i)
            try:
                subkey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f'CLSID\\{clsid}')
                try:
                    name, _ = winreg.QueryValueEx(subkey, None)
                    name_str = str(name).upper()
                    if 'MSOLAP' in name_str or 'ANALYSIS SERVICES' in name_str:
                        msolap_list.append((name, clsid))
                except:
                    pass
                winreg.CloseKey(subkey)
            except:
                pass
            i += 1
        except:
            break
    
    if msolap_list:
        print("\nFound MSOLAP providers:")
        for name, clsid in msolap_list:
            print(f"  - {name}")
            print(f"    CLSID: {clsid}")
    else:
        print("\nWARNING: No MSOLAP providers found in registry")
        print("\nSOLUTION:")
        print("Install SQL Server Management Studio (SSMS) or")
        print("Install 'SQL Server Analysis Services client tools'")
        print("Download from: https://docs.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms")
except Exception as e:
    print(f"Registry check error: {e}")