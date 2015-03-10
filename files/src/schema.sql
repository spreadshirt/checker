drop table if exists releases;
drop table if exists checklist_to_release;
drop table if exists releases_archived;
drop table if exists checklist_to_release_archived;
drop table if exists plain_checklists;
drop table if exists screenshot_checklists;
drop table if exists jenkins_checklists;
create table releases (
	  id integer primary key autoincrement,
	  name text not null,
	  placeholders text
);
create table checklist_to_release (
	  release_id integer not null,
	  checklist_type text not null,
	  checklist_id integer not null,
	  status text not null
);
create table releases_archived (
	  id integer not null,
	  name text not null,
	  placeholders text,
	  date_archived date not null
);
create table checklist_to_release_archived (
	  release_id integer not null,
	  checklist_type text not null,
	  checklist_id integer not null,
	  status text not null,
	  date_archived date not null
);
create table components (
	  id integer primary key autoincrement,
	  name text not null
);
create table checklist_to_component (
	  component_id integer not null,
	  checklist_type text not null,
	  checklist_id integer not null
);
create table plain_checklists (
	  id integer primary key autoincrement,
	  name text not null,
	  description text not null
);
create table screenshots_checklists (
	  id integer primary key autoincrement,
	  name text not null,
	  grid text not null,
	  browser text not null,
	  actual_urls text not null,
	  expected_urls text not null
);
create table jenkins_checklists (
	  id integer primary key autoincrement,
	  name text not null,
	  url text not null,
	  login text not null,
	  password text not null,
	  job text not null,
	  xml text not null
);
create table placeholders (
	  id integer primary key autoincrement,
	  name text not null,
	  default_value text
);
