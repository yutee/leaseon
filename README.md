# LeaseOn

## Description
Infrastrcutre setup to continually find the best spot machine offer form azure for deploying a machine learning model. This ensures costs are saved and there is minimal downtime.

## Tools used
- Terraform
- Azure
- Python

## The App
A machine learning model wrapped in a fastapi server that has these endspoints:
- endpoint one
- endpoint two

## The Infrastructure
This is the most interesting part.
- azure spot machine
- python program running in github actions (every 30 minutes) check for best spot machine and updates the terraform file
- when there is an eviction notice, it quickly provisions a new server using terraform and redeploys the api


### to do
- read through the notion doc
- plan steps propperly
- fix up terraform for deploying vmms
- ensure proper machines are deployed
- fix up terraform to deploy api to the vm
