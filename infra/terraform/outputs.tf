# Output values for easy access to infrastructure details

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "load_balancer_public_ip" {
  description = "Public IP address of the load balancer"
  value       = azurerm_public_ip.lb.ip_address
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "http://${azurerm_public_ip.lb.ip_address}"
}

output "api_health_check" {
  description = "Health check endpoint"
  value       = "http://${azurerm_public_ip.lb.ip_address}/health"
}

output "api_documentation" {
  description = "Interactive API documentation"
  value       = "http://${azurerm_public_ip.lb.ip_address}/docs"
}

output "vmss_name" {
  description = "Name of the Virtual Machine Scale Set"
  value       = azurerm_linux_virtual_machine_scale_set.main.name
}

output "vmss_id" {
  description = "ID of the Virtual Machine Scale Set"
  value       = azurerm_linux_virtual_machine_scale_set.main.id
}

output "current_instance_count" {
  description = "Current number of VM instances"
  value       = azurerm_linux_virtual_machine_scale_set.main.instances
}

output "vm_size" {
  description = "Size of VM instances"
  value       = local.vm_sku
}

output "spot_vm_enabled" {
  description = "Whether Spot VMs are enabled"
  value       = azurerm_linux_virtual_machine_scale_set.main.priority == "Spot"
}

output "autoscale_min_instances" {
  description = "Minimum number of instances (autoscale)"
  value       = local.vm_instances_min
}

output "autoscale_max_instances" {
  description = "Maximum number of instances (autoscale)"
  value       = local.vm_instances_max
}

output "cost_estimate" {
  description = "Estimated monthly cost (USD) - Spot VMs can be up to 90% cheaper"
  value = {
    spot_vm_cost_per_month    = "~$25-45 per VM (Standard_D2s_v3 Spot)"
    on_demand_cost_per_month  = "~$70-100 per VM (Standard_D2s_v3 On-Demand)"
    estimated_monthly_savings = "~$45-55 per VM with Spot"
    total_estimated_monthly   = "~$50-225 (depending on scale)"
    note                      = "Spot pricing varies by region and availability"
  }
}

output "useful_commands" {
  description = "Useful Azure CLI commands for managing the infrastructure"
  value = {
    check_vmss_instances    = "az vmss list-instances --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine_scale_set.main.name}"
    scale_vmss_manually     = "az vmss scale --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine_scale_set.main.name} --new-capacity 3"
    restart_vmss_instances  = "az vmss restart --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine_scale_set.main.name}"
    view_autoscale_history  = "az monitor autoscale show --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_monitor_autoscale_setting.main.name}"
    ssh_to_instance         = "az vmss list-instance-connection-info --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine_scale_set.main.name}"
  }
}

# Test endpoints to verify deployment
output "test_commands" {
  description = "Commands to test your deployed API"
  value = {
    health_check          = "curl http://${azurerm_public_ip.lb.ip_address}:80"
    # health_check          = "curl http://${azurerm_public_ip.lb.ip_address}/health"
    # get_clubs             = "curl http://${azurerm_public_ip.lb.ip_address}/clubs"
    # sample_prediction     = "curl -X POST 'http://${azurerm_public_ip.lb.ip_address}/predict' -H 'Content-Type: application/json' -d '{\"player\":{\"name\":\"Test Player\",\"age\":26,\"position\":\"Attacker\",\"market_value\":45000000,\"goals\":20},\"target_club\":\"Arsenal\"}'"
    # interactive_docs      = "Open browser: http://${azurerm_public_ip.lb.ip_address}/docs"
  }
}

output "monitoring_info" {
  description = "Monitoring and troubleshooting information"
  value = {
    resource_group         = azurerm_resource_group.main.name
    load_balancer_name     = azurerm_lb.main.name
    vmss_name             = azurerm_linux_virtual_machine_scale_set.main.name
    autoscale_setting     = azurerm_monitor_autoscale_setting.main.name
    check_lb_health       = "az network lb show --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_lb.main.name} --query 'provisioningState'"
    check_vm_instances    = "az vmss list-instances --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine_scale_set.main.name} --output table"
  }
}