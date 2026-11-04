import shutil, os
src = r'C:/Users/hachk/pilotage_b2b/ui/tabs/tab0_executive.py.bak'
dst = r'C:/Users/hachk/pilotage_b2b/ui/tabs/tab0_executive.py'
shutil.copy(src, dst)
print('Fichier restauré', os.path.getsize(dst), 'octets')
print('Chemin:', dst)