# Input variables for customizing the deployment

variable "project_name" {
  description = "Name of the project (used in resource naming)"
  type        = string
  default     = "leaseon"
  
  validation {
    condition     = length(var.project_name) <= 20 && can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must be lowercase, alphanumeric with hyphens, and max 20 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "demo"
  
  validation {
    condition     = contains(["dev", "demo"], var.environment)
    error_message = "Environment must be one of dev or demo"
  }
}

variable "location" {
  description = "Azure region for resources (cost-effective regions for students)"
  type        = string
  default     = "East US"
  
  validation {
    condition = contains([
      "East US", "East US 2", "Central US", "South Central US",
      "West Europe", "North Europe", "Southeast Asia", "Australia East"
    ], var.location)
    error_message = "Please choose a cost-effective region for student accounts."
  }
}

variable "vm_sku" {
  description = "Azure VM size for VMSS instances (Spot-compatible sizes only)"
  type        = string
  default     = "Standard_D2s_v3"  # 2 vCPU, 8GB RAM
  
  validation {
    condition = contains([
      "Standard_D2s_v3",   # 2 vCPU, 8GB RAM - recommended for ML app
      "Standard_D2s_v4",   # 2 vCPU, 8GB RAM - newer generation
      "Standard_D2s_v5",   # 2 vCPU, 8GB RAM - latest generation
      "Standard_D4s_v3",   # 4 vCPU, 16GB RAM - high performance
      "Standard_D4s_v4",   # 4 vCPU, 16GB RAM - newer generation
      "Standard_E2s_v3",   # 2 vCPU, 16GB RAM - memory optimized
      "Standard_E2s_v4",   # 2 vCPU, 16GB RAM - memory optimized
      "Standard_F2s_v2",   # 2 vCPU, 4GB RAM - compute optimized
      "Standard_F4s_v2"    # 4 vCPU, 8GB RAM - compute optimized
    ], var.vm_sku)
    error_message = "Please choose a Spot-compatible VM size. B-series VMs are not supported for Spot instances."
  }
}

variable "min_instances" {
  description = "Minimum number of VM instances in scale set"
  type        = number
  default     = 1
  
  validation {
    condition     = var.min_instances >= 1 && var.min_instances <= 10
    error_message = "Minimum instances must be between 1 and 10 for cost control."
  }
}

variable "max_instances" {
  description = "Maximum number of VM instances in scale set"
  type        = number
  default     = 2
  
  validation {
    condition     = var.max_instances >= var.min_instances && var.max_instances <= 20
    error_message = "Maximum instances must be greater than minimum and not exceed 20 for student accounts."
  }
}

variable "enable_spot_vms" {
  description = "Enable Spot VMs for cost savings (up to 90% cheaper)"
  type        = bool
  default     = true
}

variable "spot_max_price" {
  description = "Maximum price to pay for Spot VMs (-1 means pay up to on-demand price)"
  type        = number
  default     = -1
  
  validation {
    condition     = var.spot_max_price == -1 || var.spot_max_price > 0
    error_message = "Spot max price must be -1 (for on-demand price) or a positive number."
  }
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "docker_image" {
  description = "Docker image for the ML API application"
  type        = string
  default     = "football-transfer-api:latest"
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}