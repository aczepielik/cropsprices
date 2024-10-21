from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl

__all__ = [
    "Region",
    "File",
    "RelationshipData",
    "MainLinks",
    "RelationshipLinks",
    "Relationship",
    "ResourceAttributes",
    "ResourceRelationships",
    "Resource",
]


class Region(BaseModel):
    region_id: str
    hierarchy_label: str
    name: str


class File(BaseModel):
    file_size: int
    format: str
    openness_score: int
    download_url: HttpUrl


class RelationshipData(BaseModel):
    type: str
    id: str


class RelationshipLinks(BaseModel):
    related: HttpUrl


class MainLinks(BaseModel):
    self: HttpUrl


class Relationship(BaseModel):
    data: RelationshipData
    links: RelationshipLinks


class ResourceAttributes(BaseModel):
    format: str
    title: str
    is_chart_creation_blocked: bool
    has_research_data: Optional[bool] = None
    openness_score: int
    contains_protected_data: bool
    supplements: List = Field(default_factory=list)
    data_date: datetime
    has_high_value_data: Optional[bool] = None
    has_dynamic_data: Optional[bool] = None
    link: HttpUrl
    csv_download_url: Optional[HttpUrl] = None
    csv_file_url: Optional[HttpUrl] = None
    modified: datetime
    visualization_types: List = Field(default_factory=list)
    verified: datetime
    media_type: str
    special_signs: List = Field(default_factory=list)
    downloads_count: int
    description: str
    regions: List[Region]
    download_url: HttpUrl
    jsonld_download_url: Optional[HttpUrl] = None
    file_size: int
    jsonld_file_size: Optional[int] = None
    views_count: int
    jsonld_file_url: Optional[HttpUrl] = None
    csv_file_size: Optional[int] = None
    files: List[File]
    language: str
    created: datetime
    file_url: HttpUrl


class ResourceRelationships(BaseModel):
    institution: Relationship
    dataset: Relationship


class Resource(BaseModel):
    type: str
    attributes: ResourceAttributes
    relationships: ResourceRelationships
    id: str
    links: MainLinks
