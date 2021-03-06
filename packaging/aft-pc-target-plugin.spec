#
# Copyright (c) 2013, 2014, 2015 Intel, Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2 of the License
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

Name:       aft-pc-target-plugin
Summary:    AFT plugin for PC-like devices
Version:    0.4.2
Release:    1
Group:      Development/Tools
License:    GPL-2.0
BuildArch:  noarch
URL:        http://otctools.jf.intel.com
Source:     %{name}-%{version}.tar.gz

BuildRequires: python
BuildRequires: python-setuptools
BuildRequires: fdupes

Requires: python-setuptools
Requires: aft-core
Requires: pem

%define     base_project_name aft
%define     plugin_name pc

%description
AFT plugin supporting PC-like devices.

%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf %{buildroot}
%{__python} setup.py install -O2 --root=%{buildroot} --prefix=%{_prefix}
%fdupes %{buildroot}


%files
%defattr(-,root,root,-)
%{python_sitelib}/%{plugin_name}-%{version}-*.egg-info
%{python_sitelib}/%{base_project_name}


%changelog
