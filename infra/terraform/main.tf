# Configure Terraform and Required Providers

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  backend "azurerm" {
    resource_group_name  = "terraformstatesRG"
    storage_account_name = "terraformstate737"
    container_name       = "tfstateblob"
    key                  = "leaseon/terraform.tfstate"
  }
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Generate random suffix for unique naming
resource "random_id" "suffix" {
  byte_length = 4
}

# Local variables for consistent naming and configuration
locals {
  project_name = "leaseon"
  environment  = "demo"
  location     = "East US"  # Cost-effective region for students
  
  # Naming convention
  prefix = "${local.project_name}-${local.environment}"
  suffix = random_id.suffix.hex
  
  # VMSS Configuration
  vm_sku           = "Standard_D2s_v3"  # 2 vCPU, 8GB RAM - Spot compatible for ML app
  vm_instances_min = 1                  # Minimum instances for availability
  vm_instances_max = 2                 # Maximum instances for scaling
  
  # Network Configuration
  vnet_address_space = "10.0.0.0/16"
  subnet_address     = "10.0.1.0/24"
  subnet_address_2   = "10.0.2.0/24"
  
  # Common tags
  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
    Purpose     = "ML-API-Hosting"
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${local.prefix}-rg-${local.suffix}"
  location = local.location
  tags     = local.common_tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${local.prefix}-vnet-${local.suffix}"
  address_space       = [local.vnet_address_space]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

# Subnet for VMSS
resource "azurerm_subnet" "vmss" {
  name                 = "${local.prefix}-subnet-vmss"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [local.subnet_address]
}

# Subnet for Load Balancer (required for Standard LB)
resource "azurerm_subnet" "lb" {
  name                 = "${local.prefix}-subnet-lb"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [local.subnet_address_2]
}

# Network Security Group for VMSS
resource "azurerm_network_security_group" "vmss" {
  name                = "${local.prefix}-nsg-vmss-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
  name                       = "AllowHTTPFromInternet"
  priority                   = 1000
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "8000"
  source_address_prefix      = "*"
  destination_address_prefix = "*"
  }

  # Allow HTTP traffic from Load Balancer
  security_rule {
    name                       = "AllowHTTPFromLB"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8000"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }

  # Allow SSH
  security_rule {
    name                       = "AllowSSH"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow internet access
  security_rule {
    name                       = "AllowOutboundInternet"
    priority                   = 1003
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "Internet"
  }

  tags = local.common_tags
}

# Associate NSG with VMSS subnet
resource "azurerm_subnet_network_security_group_association" "vmss" {
  subnet_id                 = azurerm_subnet.vmss.id
  network_security_group_id = azurerm_network_security_group.vmss.id
}

# Public IP for Load Balancer
resource "azurerm_public_ip" "lb" {
  name                = "${local.prefix}-lb-public-ip-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  tags                = local.common_tags
}

# Load Balancer
resource "azurerm_lb" "main" {
  name                = "${local.prefix}-lb-${local.suffix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  sku_tier            = "Regional"

  frontend_ip_configuration {
    name                 = "PublicIPAddress"
    public_ip_address_id = azurerm_public_ip.lb.id
  }

  tags = local.common_tags
}

# Load Balancer Backend Pool
resource "azurerm_lb_backend_address_pool" "main" {
  loadbalancer_id = azurerm_lb.main.id
  name            = "${local.prefix}-backend-pool"
}

# Load Balancer Health Probe
resource "azurerm_lb_probe" "health" {
  loadbalancer_id = azurerm_lb.main.id
  name            = "health-probe"
  port            = 8000
  protocol        = "Http"
  request_path    = "/health"
  interval_in_seconds         = 15
  number_of_probes           = 2
}

# Load Balancer Rule
resource "azurerm_lb_rule" "http" {
  loadbalancer_id                = azurerm_lb.main.id
  name                           = "HTTPRule"
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 8000
  frontend_ip_configuration_name = "PublicIPAddress"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.main.id]
  probe_id                       = azurerm_lb_probe.health.id
  disable_outbound_snat          = true
}

# Load Balancer Outbound Rule (for internet access from VMs)
resource "azurerm_lb_outbound_rule" "internet" {
  name                    = "OutboundRule"
  loadbalancer_id         = azurerm_lb.main.id
  protocol                = "All"
  backend_address_pool_id = azurerm_lb_backend_address_pool.main.id

  frontend_ip_configuration {
    name = "PublicIPAddress"
  }
}

resource "azurerm_lb_nat_pool" "ssh" {
  resource_group_name            = azurerm_resource_group.main.name
  name                           = "ssh-nat-pool"
  loadbalancer_id                = azurerm_lb.main.id
  protocol                       = "Tcp"
  frontend_port_start            = 50000
  frontend_port_end              = 50019
  backend_port                   = 22
  frontend_ip_configuration_name = "PublicIPAddress"
}


# Cloud-init script for VM setup
# locals {
#   cloud_init = base64encode(templatefile("${path.module}/cloudinit.yaml", {
#     docker_image = "utibeokon/ml-app-api:amd-latest"
#   }))
# }

locals {
  cloud_init = base64encode(templatefile("${path.module}/cloudinit.yaml", {}))
}

# Virtual Machine Scale Set
resource "azurerm_linux_virtual_machine_scale_set" "main" {
  name                = "${local.prefix}-vmss-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = local.vm_sku
  instances           = local.vm_instances_min
  
  # Spot VM Configuration - Up to 90% cost savings!
  priority        = "Spot"
  eviction_policy = "Delete"  # Delete VMs when evicted (cheaper than Deallocate)
  
  # Max price you're willing to pay (-1 means pay up to on-demand price)
  max_bid_price = -1
  
  # Enable automatic repairs
  upgrade_mode = "Automatic"
  
  # Health monitoring
  health_probe_id = azurerm_lb_probe.health.id
  
  # Availability zones for better availability
  zones = ["1", "2", "3"]
  
  # Scale set will spread instances across zones
  zone_balance = true
  
  # Platform fault domain count (max spreading)
  # platform_fault_domain_count = 1

  # Disable authentication with password (SSH key only)
  disable_password_authentication = true

  # VM Image
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # OS Disk
  os_disk {
    storage_account_type = "Standard_LRS"
    caching              = "ReadWrite"
    disk_size_gb         = 30
  }

  # Admin user
  admin_username = "azureuser"

  # SSH Key
  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  # Network Interface
  network_interface {
    name    = "internal"
    primary = true

    ip_configuration {
      name                                   = "internal"
      primary                                = true
      subnet_id                              = azurerm_subnet.vmss.id
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.main.id]
      load_balancer_inbound_nat_rules_ids    = [azurerm_lb_nat_pool.ssh.id]
    }
  }

  # Cloud-init for application setup
  custom_data = local.cloud_init

  # Automatic instance repairs
  automatic_instance_repair {
    enabled      = true
    grace_period = "PT30M"  # 30 minutes grace period
  }

  tags = local.common_tags

  depends_on = [
    azurerm_lb_probe.health,
    azurerm_lb_rule.http
  ]
}

# Auto-scaling configuration
resource "azurerm_monitor_autoscale_setting" "main" {
  name                = "${local.prefix}-autoscale-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  target_resource_id  = azurerm_linux_virtual_machine_scale_set.main.id

  profile {
    name = "default"

    capacity {
      default = local.vm_instances_min
      minimum = local.vm_instances_min
      maximum = local.vm_instances_max
    }

    # Scale out rule (increase instances when CPU > 75%)
    rule {
      metric_trigger {
        metric_name        = "Percentage CPU"
        metric_resource_id = azurerm_linux_virtual_machine_scale_set.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 75
      }

      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }

    # Scale in rule (decrease instances when CPU < 25%)
    rule {
      metric_trigger {
        metric_name        = "Percentage CPU"
        metric_resource_id = azurerm_linux_virtual_machine_scale_set.main.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 25
      }

      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }
  }

  tags = local.common_tags
}