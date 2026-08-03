Attribute VB_Name = "CRM_Module"

Sub Refresh_CRM()
    RunPython ("import crm; crm.update_crm_dashboard()")
End Sub

Sub Export_CRM_Data()
    RunPython ("import crm; crm.export_to_excel(crm.load_crm_data())")
End Sub

Sub Create_CRM_Pivots()
    RunPython ("import crm; crm.create_pivot_tables()")
End Sub
