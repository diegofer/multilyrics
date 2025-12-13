from invoke import task as local_task

# ejecutar tarea local para compilar archivos .ui de Qt Designer
@local_task
def compile_ui(c):   
    c.run("pyside6-uic ui/main_window.ui -o ui/main_window_ui.py")
    print("Archivos .ui compilados correctamente.") 
    