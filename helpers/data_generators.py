"""
Data generators for test data creation.

This module provides utilities to generate realistic test data for load testing
and performance testing, including organizational structures, users, positions, and projects.
"""

import requests
from faker import Faker
from typing import Dict, List, Optional, Any
import time

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Organizational Structure Configuration
ORG_DEPTH_LEVELS = 3  # Number of levels of depth after level 1 (excluding root departments)
SUB_DEPARTMENTS_PER_LEVEL = 3  # Number of sub-departments per department at each level
POSITIONS_PER_DEPARTMENT = 5  # Number of positions per department

# Data Generation Volumes
NB_USERS = 100  # Total number of users to generate
NB_PROJECTS = 50  # Total number of projects to generate (future use)

# Root Level Organization Structure (Matricial Organization)
# Level 0: Main departments
COMPETENCE_CENTERS = [
    {
        "name": "Direction Ingénierie",
        "description": "Centre de compétences ingénierie",
        "sub_departments": ["Mécanique", "Électronique", "Logiciel"]
    },
    {
        "name": "Direction Industrielle",
        "description": "Centre de compétences industriel",
        "sub_departments": ["Industrialisation", "Production", "SAV"]
    },
    {
        "name": "Direction Support",
        "description": "Fonctions support",
        "sub_departments": ["Achats", "Ressources Humaines"]
    }
]

BUSINESS_LINES = [
    {
        "name": "Business Line Commerce",
        "description": "Ligne métier commerce",
        "sub_departments": ["Ventes France", "Ventes Export"]
    },
    {
        "name": "Business Line Affaires",
        "description": "Ligne métier affaires",
        "sub_departments": ["Grands Comptes", "PME/ETI"]
    },
    {
        "name": "Business Line Innovation",
        "description": "Ligne métier innovation",
        "sub_departments": ["R&D Produits", "R&D Procédés"]
    },
    {
        "name": "Business Line Services",
        "description": "Ligne métier services",
        "sub_departments": ["Conseil", "Maintenance"]
    }
]


# =============================================================================
# DATA GENERATOR CLASS
# =============================================================================

class DataGenerator:
    """
    Generate realistic test data for API testing and load testing.
    
    This class uses Faker to generate realistic French data and provides methods
    to create organizational structures, users, and positions via API calls.
    
    Example usage:
        ```python
        generator = DataGenerator(
            base_url="http://localhost:5002",
            cookies={'access_token': 'xxx', 'refresh_token': 'yyy'},
            company_id="123e4567-e89b-12d3-a456-426614174000"
        )
        
        # Generate organizational structure
        org_data = generator.generate_organization_structure()
        
        # Generate users
        users = generator.generate_users(count=50)
        
        # Cleanup
        generator.cleanup()
        ```
    """
    
    def __init__(
        self, 
        base_url: str,
        cookies: Dict[str, str],
        company_id: str,
        locale: str = 'fr_FR'
    ):
        """
        Initialize the data generator.
        
        Args:
            base_url: Base URL of the API (e.g., "http://localhost:5002")
            cookies: Authentication cookies dict {'access_token': '...', 'refresh_token': '...'}
            company_id: Company UUID for multi-tenant isolation
            locale: Faker locale for data generation (default: 'fr_FR')
        """
        self.base_url = base_url
        self.cookies = cookies
        self.company_id = company_id
        self.fake = Faker(locale)
        self.session = requests.Session()
        
        # Track created resources for cleanup
        self.created_org_units: List[str] = []
        self.created_positions: List[str] = []
        self.created_users: List[str] = []
        self.created_projects: List[str] = []
    
    # =========================================================================
    # ORGANIZATION STRUCTURE GENERATION
    # =========================================================================
    
    def generate_organization_structure(self) -> Dict[str, Any]:
        """
        Generate a complete organizational structure with multiple levels.
        
        Creates a matricial organization with:
        - 1 root level: Direction Générale
        - 3 competence centers (Ingénierie, Industrielle, Support)
        - 4 business lines
        - Configurable depth levels with sub-departments
        - Positions for each department
        
        Returns:
            Dict containing:
                - 'organization_units': List of all created org units with IDs
                - 'positions': List of all created positions with IDs
                - 'hierarchy': Dict mapping parent_id to children
        """
        print("🏢 Generating organizational structure...")
        
        org_units = []
        positions = []
        hierarchy = {}
        
        # Create root level: Direction Générale
        print("  🏛️ Creating root level: Direction Générale...")
        direction_generale = self._create_organization_unit(
            name="Direction Générale",
            description="Direction Générale de l'entreprise"
        )
        org_units.append(direction_generale)
        
        # Create position for Direction Générale
        dg_position = self._create_position(
            title="Directeur Général",
            organization_unit_id=direction_generale['id']
        )
        positions.append(dg_position)
        
        # Generate Competence Centers under Direction Générale
        print("  📊 Creating competence centers...")
        for center in COMPETENCE_CENTERS:
            center_data = self._create_organization_unit(
                name=center['name'],
                description=center['description'],
                parent_id=direction_generale['id']
            )
            org_units.append(center_data)
            
            # Create directeur position for this center
            director_position = self._create_position(
                title=f"Directeur {center['name']}",
                organization_unit_id=center_data['id']
            )
            positions.append(director_position)
            
            # Generate level 1 sub-departments
            for sub_dept_name in center['sub_departments']:
                sub_dept = self._create_organization_unit(
                    name=f"{center['name']} - {sub_dept_name}",
                    description=f"Département {sub_dept_name}",
                    parent_id=center_data['id']
                )
                org_units.append(sub_dept)
                
                # Generate additional depth levels
                positions.extend(
                    self._generate_department_tree(
                        parent_unit=sub_dept,
                        depth=ORG_DEPTH_LEVELS,
                        org_units_list=org_units
                    )
                )
        
        # Generate Business Lines under Direction Générale
        print("  💼 Creating business lines...")
        for bl in BUSINESS_LINES:
            bl_data = self._create_organization_unit(
                name=bl['name'],
                description=bl['description'],
                parent_id=direction_generale['id']
            )
            org_units.append(bl_data)
            
            # Create directeur position for this business line
            director_position = self._create_position(
                title=f"Directeur {bl['name']}",
                organization_unit_id=bl_data['id']
            )
            positions.append(director_position)
            
            # Generate level 1 sub-departments
            for sub_dept_name in bl['sub_departments']:
                sub_dept = self._create_organization_unit(
                    name=f"{bl['name']} - {sub_dept_name}",
                    description=f"Département {sub_dept_name}",
                    parent_id=bl_data['id']
                )
                org_units.append(sub_dept)
                
                # Generate additional depth levels
                positions.extend(
                    self._generate_department_tree(
                        parent_unit=sub_dept,
                        depth=ORG_DEPTH_LEVELS,
                        org_units_list=org_units
                    )
                )
        
        # Build hierarchy mapping
        for unit in org_units:
            parent_id = unit.get('parent_id')
            if parent_id:
                if parent_id not in hierarchy:
                    hierarchy[parent_id] = []
                hierarchy[parent_id].append(unit['id'])
        
        print(f"✅ Created {len(org_units)} organization units")
        print(f"✅ Created {len(positions)} positions")
        
        return {
            'organization_units': org_units,
            'positions': positions,
            'hierarchy': hierarchy
        }
    
    def _generate_department_tree(
        self, 
        parent_unit: Dict[str, Any],
        depth: int,
        org_units_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Recursively generate sub-departments and positions.
        
        Args:
            parent_unit: Parent organization unit dict
            depth: Number of levels to generate
            org_units_list: List to append created org units to
            
        Returns:
            List of created positions
        """
        positions = []
        
        # Create positions for current department
        for _ in range(POSITIONS_PER_DEPARTMENT):
            position = self._create_position(
                title=self._generate_position_title(parent_unit.get('name')),
                organization_unit_id=parent_unit['id']
            )
            positions.append(position)
        
        # Recursively create sub-departments if depth > 0
        if depth > 0:
            for _ in range(SUB_DEPARTMENTS_PER_LEVEL):
                sub_unit = self._create_organization_unit(
                    name=f"{parent_unit['name']} - {self.fake.catch_phrase()}",
                    description=f"Sous-département niveau {ORG_DEPTH_LEVELS - depth + 1}",
                    parent_id=parent_unit['id']
                )
                org_units_list.append(sub_unit)
                
                # Recursive call
                positions.extend(
                    self._generate_department_tree(
                        parent_unit=sub_unit,
                        depth=depth - 1,
                        org_units_list=org_units_list
                    )
                )
        
        return positions
    
    # =========================================================================
    # USER GENERATION (TO BE IMPLEMENTED LATER)
    # =========================================================================
    
    # TODO: Implement user generation when needed
    
    # =========================================================================
    # PROJECT GENERATION (PLACEHOLDER)
    # =========================================================================
    
    def generate_projects(
        self, 
        count: Optional[int] = None,
        organization_unit_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic projects.
        
        NOTE: This is a placeholder for future implementation when Project API is available.
        
        Args:
            count: Number of projects to generate (default: NB_PROJECTS constant)
            organization_unit_ids: Optional list of org unit IDs to associate projects with
            
        Returns:
            List of created project dicts with IDs
        """
        if count is None:
            count = NB_PROJECTS
        
        print(f"📋 Project generation not yet implemented (placeholder for {count} projects)")
        return []
    
    # =========================================================================
    # API HELPERS
    # =========================================================================
    
    def _create_organization_unit(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an organization unit via API."""
        
        # Ensure name doesn't exceed 100 characters (API limit)
        max_name_length = 100
        final_name = name[:max_name_length] if len(name) > max_name_length else name
        
        data = {
            "name": final_name,
            "company_id": self.company_id,
            "description": description or name
        }
        
        if parent_id:
            data["parent_id"] = parent_id
        
        response = self.session.post(
            f"{self.base_url}/api/identity/organization_units",
            json=data,
            cookies=self.cookies
        )
        
        if response.status_code != 201:
            raise Exception(
                f"Failed to create organization unit: {response.status_code} - {response.text}"
            )
        
        result = response.json()
        self.created_org_units.append(result['id'])
        return result
    
    def _create_position(
        self,
        title: str,
        organization_unit_id: str
    ) -> Dict[str, Any]:
        """Create a position via API."""
        data = {
            "title": title,
            "company_id": self.company_id,
            "organization_unit_id": organization_unit_id
        }
        
        response = self.session.post(
            f"{self.base_url}/api/identity/positions",
            json=data,
            cookies=self.cookies
        )
        
        if response.status_code != 201:
            raise Exception(
                f"Failed to create position: {response.status_code} - {response.text}"
            )
        
        result = response.json()
        self.created_positions.append(result['id'])
        return result
    
    def _create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a user via API."""
        response = self.session.post(
            f"{self.base_url}/api/identity/users",
            json=user_data,
            cookies=self.cookies
        )
        
        if response.status_code != 201:
            raise Exception(
                f"Failed to create user: {response.status_code} - {response.text}"
            )
        
        result = response.json()
        self.created_users.append(result['id'])
        return result
    
    def _generate_position_title(self, department_name: Optional[str] = None) -> str:
        """
        Generate a realistic position title in French based on department context.
        
        Args:
            department_name: Optional department name to generate contextual titles
            
        Returns:
            Realistic position title
        """
        # Engineering-specific titles
        engineering_titles = [
            "Ingénieur Logiciel", "Ingénieur DevOps", "Architecte Logiciel",
            "Développeur Full Stack", "Développeur Backend", "Développeur Frontend",
            "Ingénieur QA", "Testeur", "Ingénieur Système",
            "Ingénieur Mécanique", "Ingénieur Électronique", "Ingénieur R&D",
            "Chef de Projet Technique", "Tech Lead", "Scrum Master"
        ]
        
        # Industrial/Production titles
        industrial_titles = [
            "Responsable Production", "Chef d'Atelier", "Technicien de Production",
            "Opérateur de Production", "Contrôleur Qualité", "Responsable Qualité",
            "Ingénieur Industrialisation", "Technicien Maintenance", "Responsable SAV",
            "Ingénieur Méthodes", "Préparateur", "Logisticien"
        ]
        
        # Business/Commercial titles
        business_titles = [
            "Ingénieur Commercial", "Chef des Ventes", "Responsable Compte-Clé",
            "Business Developer", "Chargé d'Affaires", "Account Manager",
            "Responsable Commercial", "Technico-Commercial", "Inside Sales",
            "Customer Success Manager", "Key Account Manager"
        ]
        
        # Support/Admin titles
        support_titles = [
            "Responsable RH", "Chargé de Recrutement", "Assistant RH",
            "Responsable Achats", "Acheteur", "Approvisionneur",
            "Contrôleur de Gestion", "Comptable", "Assistant Administratif",
            "Responsable Juridique", "Office Manager", "Assistant de Direction"
        ]
        
        # Innovation/R&D titles
        innovation_titles = [
            "Chercheur R&D", "Ingénieur Innovation", "Chef de Projet R&D",
            "Responsable Innovation", "Data Scientist", "Analyste",
            "Consultant Innovation", "Expert Technique", "Spécialiste Procédés"
        ]
        
        # Generic management titles (applicable to any department)
        management_titles = [
            "Directeur", "Directeur Adjoint", "Manager",
            "Chef de Service", "Responsable d'Équipe", "Coordinateur"
        ]
        
        # Determine which category to use based on department name
        if department_name:
            dept_lower = department_name.lower()
            
            # Engineering departments
            if any(kw in dept_lower for kw in ['ingénierie', 'logiciel', 'électronique', 'mécanique', 'r&d produits']):
                return self.fake.random_element(engineering_titles + management_titles)
            
            # Industrial departments
            elif any(kw in dept_lower for kw in ['industriel', 'production', 'industrialisation', 'sav', 'maintenance']):
                return self.fake.random_element(industrial_titles + management_titles)
            
            # Business departments
            elif any(kw in dept_lower for kw in ['commerce', 'affaires', 'ventes', 'commercial', 'business']):
                return self.fake.random_element(business_titles + management_titles)
            
            # Support departments
            elif any(kw in dept_lower for kw in ['support', 'rh', 'ressources humaines', 'achats', 'juridique']):
                return self.fake.random_element(support_titles + management_titles)
            
            # Innovation departments
            elif any(kw in dept_lower for kw in ['innovation', 'r&d', 'procédés', 'recherche']):
                return self.fake.random_element(innovation_titles + management_titles)
        
        # Fallback: random from all categories
        all_titles = (engineering_titles + industrial_titles + business_titles + 
                     support_titles + innovation_titles + management_titles)
        return self.fake.random_element(all_titles)
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup(self) -> None:
        """
        Delete all created resources.
        
        Since we create a single root "Direction Générale" without timestamp,
        we can simply delete this root node and the database cascade will
        handle all children (positions and organization units).
        """
        print("🧹 Cleaning up generated data...")
        
        # Find the Direction Générale root unit
        direction_generale_id = None
        for unit_id in self.created_org_units:
            # The first created unit should be Direction Générale
            direction_generale_id = unit_id
            break
        
        if direction_generale_id:
            try:
                print("  🗑️ Deleting root unit 'Direction Générale' (cascade delete)...")
                response = self.session.delete(
                    f"{self.base_url}/api/identity/organization_units/{direction_generale_id}",
                    cookies=self.cookies
                )
                if response.status_code == 204:
                    print("  ✅ Deleted Direction Générale and all children (cascade)")
                else:
                    print(f"  ⚠️ Failed to delete Direction Générale: {response.status_code}")
            except Exception as e:
                print(f"  ⚠️ Error deleting Direction Générale: {e}")
        else:
            print("  ⚠️ No Direction Générale found to delete")
        
        print("✅ Cleanup completed")
        
        # Clear tracking lists
        self.created_users.clear()
        self.created_positions.clear()
        self.created_org_units.clear()
        self.created_projects.clear()
