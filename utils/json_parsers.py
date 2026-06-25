"""JSON parsers for different operational signals file types."""

from typing import Dict, Any, Optional
import re


class JSONParserRegistry:
    """Registry for JSON file parsers."""
    
    def __init__(self):
        self.parsers = {
            "active_critical_immediate_alerts.json": self._parse_active_critical_alerts,
            "clusters_needing_attention.json": self._parse_clusters_needing_attention,
            "esxi_hosts_needing_attention.json": self._parse_esxi_hosts_needing_attention,
            "management_vms_needing_attention.json": self._parse_management_vms_needing_attention,
            "nfs_datastores_needing_attention.json": self._parse_nfs_datastores_needing_attention,
            "nsx_alarms.json": self._parse_nsx_alarms,
            "provider_vdcs_needing_attention.json": self._parse_provider_vdcs_needing_attention,
            "vcenter_alarms.json": self._parse_vcenter_alarms,
            "vcloud_director_cells_needing_attention.json": self._parse_vcloud_director_cells_needing_attention,
            "vsan_clusters_needing_attention.json": self._parse_vsan_clusters_needing_attention,
        }
    
    def parse(self, filename: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse JSON data based on filename.
        
        Args:
            filename: Name of the JSON file
            data: Raw JSON data
            
        Returns:
            Optional[Dict]: Parsed data structure or None
        """
        parser = self.parsers.get(filename)
        if parser:
            return parser(data)
        else:
            # Fallback to generic parser
            return self._parse_generic(data)
    
    def _parse_active_critical_alerts(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse active_critical_immediate_alerts.json.
        
        Structure: alerts -> {Category} -> {Alert Name} -> [Resources]
        """
        if "alerts" not in data or not isinstance(data["alerts"], dict):
            return None
        
        alerts_data = data["alerts"]
        total_count = 0
        categories = {}
        
        for category_name, alert_dict in alerts_data.items():
            if isinstance(alert_dict, dict):
                category_alerts = {}
                category_count = 0
                
                for alert_name, resources in alert_dict.items():
                    if isinstance(resources, list):
                        resource_count = len(resources)
                        category_count += resource_count
                        total_count += resource_count
                        
                        category_alerts[alert_name] = {
                            "count": resource_count,
                            "resources": resources
                        }
                
                if category_alerts:
                    # Format category name
                    formatted_category = self._format_category_name(category_name)
                    categories[formatted_category] = {
                        "count": category_count,
                        "alerts": category_alerts
                    }
        
        if categories:
            return {
                "count": total_count,
                "structure": "hierarchical",
                "categories": categories
            }
        
        return None
    
    def _parse_clusters_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse clusters_needing_attention.json.
        
        Structure: clusters -> {Issue Type} -> [Cluster Objects]
        Returns a flat structure with issue types as top-level items.
        """
        if "clusters" not in data or not isinstance(data["clusters"], dict):
            return None
        
        clusters_data = data["clusters"]
        total_count = 0
        issues = []
        
        for issue_type, cluster_list in clusters_data.items():
            if isinstance(cluster_list, list) and cluster_list:
                total_count += len(cluster_list)
                
                # Create an issue entry for each issue type
                issues.append({
                    "issue_type": issue_type,
                    "count": len(cluster_list),
                    "clusters": cluster_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "clusters",  # Special structure type
                "issues": issues
            }
        
        return None
    
    def _parse_esxi_hosts_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse esxi_hosts_needing_attention.json."""
        return self._parse_generic(data)
    
    def _parse_management_vms_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse management_vms_needing_attention.json.
        
        Structure: managementVms -> {Issue Type} -> [VM Objects]
        Returns a vms structure with issue types as top-level items.
        """
        if "managementVms" not in data or not isinstance(data["managementVms"], dict):
            return None
        
        vms_data = data["managementVms"]
        total_count = 0
        issues = []
        
        for issue_type, vm_list in vms_data.items():
            if isinstance(vm_list, list) and vm_list:
                total_count += len(vm_list)
                
                # Create an issue entry for each issue type
                issues.append({
                    "issue_type": issue_type,
                    "count": len(vm_list),
                    "vms": vm_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "vms",  # Special structure type for VMs
                "issues": issues
            }
        
        return None
    
    def _parse_nfs_datastores_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse nfs_datastores_needing_attention.json.
        
        Structure: nfsDatastores -> {Issue Type} -> [Datastore Objects]
        Returns a datastores structure with issue types as top-level items.
        """
        if "nfsDatastores" not in data or not isinstance(data["nfsDatastores"], dict):
            return None
        
        datastores_data = data["nfsDatastores"]
        total_count = 0
        issues = []
        
        for issue_type, datastore_list in datastores_data.items():
            if isinstance(datastore_list, list) and datastore_list:
                total_count += len(datastore_list)
                
                # Create an issue entry for each issue type
                issues.append({
                    "issue_type": issue_type,
                    "count": len(datastore_list),
                    "datastores": datastore_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "datastores",  # Special structure type for datastores
                "issues": issues
            }
        
        return None
    
    def _parse_nsx_alarms(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse nsx_alarms.json.
        
        Structure: nsxAlarms -> {Alarm Type} -> [Alarm Objects]
        Returns an alarms structure with alarm types as top-level items.
        """
        if "nsxAlarms" not in data or not isinstance(data["nsxAlarms"], dict):
            return None
        
        alarms_data = data["nsxAlarms"]
        total_count = 0
        issues = []
        
        for alarm_type, alarm_list in alarms_data.items():
            if isinstance(alarm_list, list) and alarm_list:
                total_count += len(alarm_list)
                
                # Create an issue entry for each alarm type
                issues.append({
                    "issue_type": alarm_type,
                    "count": len(alarm_list),
                    "alarms": alarm_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "alarms",  # Special structure type for alarms
                "issues": issues
            }
        
        return None
    
    def _parse_provider_vdcs_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse provider_vdcs_needing_attention.json.
        
        Structure: providerVdcs -> {Issue Type} -> [Provider VDC Objects]
        Returns a provider_vdcs structure with issue types as top-level items.
        """
        if "providerVdcs" not in data or not isinstance(data["providerVdcs"], dict):
            return None
        
        provider_vdcs_data = data["providerVdcs"]
        total_count = 0
        issues = []
        
        for issue_type, vdc_list in provider_vdcs_data.items():
            if isinstance(vdc_list, list) and vdc_list:
                total_count += len(vdc_list)
                
                # Create an issue entry for each issue type
                issues.append({
                    "issue_type": issue_type,
                    "count": len(vdc_list),
                    "provider_vdcs": vdc_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "provider_vdcs",  # Special structure type for provider VDCs
                "issues": issues
            }
        
        return None
    
    def _parse_vcenter_alarms(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse vcenter_alarms.json.
        
        Structure: vcenterAlarms -> {Alarm Type} -> [Alarm Objects with vm_name, status, time]
        Returns a vcenter_alarms structure with alarm types as top-level items.
        """
        if "vcenterAlarms" not in data or not isinstance(data["vcenterAlarms"], dict):
            return None
        
        vcenter_alarms_data = data["vcenterAlarms"]
        total_count = 0
        issues = []
        
        for alarm_type, alarm_list in vcenter_alarms_data.items():
            if isinstance(alarm_list, list) and alarm_list:
                total_count += len(alarm_list)
                
                # Create an issue entry for each alarm type
                issues.append({
                    "issue_type": alarm_type,
                    "count": len(alarm_list),
                    "vcenter_alarms": alarm_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "vcenter_alarms",  # Special structure type for vCenter alarms
                "issues": issues
            }
        
        return None
    
    def _parse_vcloud_director_cells_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse vcloud_director_cells_needing_attention.json.
        
        Structure: directorCells -> {Issue Type} -> [Director Cell Objects]
        Returns a director_cells structure with issue types as top-level items.
        """
        if "directorCells" not in data or not isinstance(data["directorCells"], dict):
            return None
        
        director_cells_data = data["directorCells"]
        total_count = 0
        issues = []
        
        for issue_type, cell_list in director_cells_data.items():
            if isinstance(cell_list, list) and cell_list:
                total_count += len(cell_list)
                
                # Create an issue entry for each issue type
                issues.append({
                    "issue_type": issue_type,
                    "count": len(cell_list),
                    "director_cells": cell_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "director_cells",  # Special structure type for director cells
                "issues": issues
            }
        
        return None
    
    def _parse_vsan_clusters_needing_attention(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse vsan_clusters_needing_attention.json.
        
        Structure: vsanClusters -> {Issue Type} -> [vSAN Cluster Objects]
        Returns a vsan_clusters structure with issue types as top-level items.
        """
        if "vsanClusters" not in data or not isinstance(data["vsanClusters"], dict):
            return None
        
        vsan_clusters_data = data["vsanClusters"]
        total_count = 0
        issues = []
        
        for issue_type, cluster_list in vsan_clusters_data.items():
            if isinstance(cluster_list, list) and cluster_list:
                total_count += len(cluster_list)
                
                # Create an issue entry for each issue type
                issues.append({
                    "issue_type": issue_type,
                    "count": len(cluster_list),
                    "vsan_clusters": cluster_list
                })
        
        if issues:
            return {
                "count": total_count,
                "structure": "vsan_clusters",  # Special structure type for vSAN clusters
                "issues": issues
            }
        
        return None
    
    def _parse_generic(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generic parser for unknown structures."""
        # Try to find lists or arrays in the data
        issues = []
        
        if isinstance(data, dict):
            # Try common keys
            for key in ['issues', 'alerts', 'items', 'data', 'records', 'clusters', 'hosts', 'vms', 'datastores']:
                if key in data and isinstance(data[key], list):
                    issues = data[key]
                    break
            
            # If no standard key, look for any list
            if not issues:
                for value in data.values():
                    if isinstance(value, list) and value:
                        issues = value
                        break
            
            # If still nothing, wrap the dict
            if not issues and data:
                issues = [data]
        elif isinstance(data, list):
            issues = data
        
        if issues:
            return {
                "count": len(issues),
                "structure": "flat",
                "issues": issues
            }
        
        return None
    
    def _format_category_name(self, name: str) -> str:
        """Format category name for display.
        
        Args:
            name: Raw category name (e.g., 'VirtualMachine', 'HostSystem')
            
        Returns:
            str: Formatted name (e.g., 'Virtual Machine', 'Host System')
        """
        # Replace underscores with spaces
        name = name.replace("_", " ")
        
        # Add spaces before capital letters
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        
        return name


# Global parser registry instance
parser_registry = JSONParserRegistry()

# Made with Bob
