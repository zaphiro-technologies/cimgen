# <img src="documentation/images/cimgen_logo.png" alt="CIMgen" width=120 />

Python tool for code generation from CIM data model for several programming languages

## Concept overview

![Overview CIMgen](documentation/images/CIMgen.svg)

## Usage example

### Generating C++ files

#### Generating C++ files on Linux

```bash
pip install -e .
cimgen --outdir=output/cpp/CGMES_2.4.15_27JAN2020 --schemadir=cgmes_schema/CGMES_2.4.15_27JAN2020 --langdir=cpp --cgmes_version=cgmes_v2_4_15
```

This will build version `CGMES_2.4.15_27JAN2020` in the subfolder `output/cpp/CGMES_2.4.15_27JAN2020`.

> [!NOTE]
> If you wish to build an alternative version, you can see available options in the subfolder called `cgmes_schema`.
> For the schema `CGMES_3.0.0` you have to use the option
> `--cgmes_version=cgmes_v3_0_0`. `outdir` can be set to whichever absolute path you wish to create the files in.

Alternatively, you can leverage `Makefile`:

```bash
pip install -e .
#unset BUILD_IN_DOCKER # if you previously set to use docker
#export SCHEMA=CGMES_3.0.0 # to use CGMES 3.0.0
make cpp
```

#### Generating C++ files in a Docker container

```bash
docker build --tag cimgen --file Dockerfile .
docker run --volume "$(pwd)/output:/output" cimgen --outdir=/output/cpp/CGMES_2.4.15_27JAN2020 --schemadir=/cimgen/cgmes_schema/CGMES_2.4.15_27JAN2020 --langdir=cpp --cgmes_version=cgmes_v2_4_15
```

alternatively, you can leverage `Makefile`:

```bash
export BUILD_IN_DOCKER=true
#export SCHEMA=CGMES_3.0.0 to use CGMES 3.0.0
make cpp
```

### Generating Python files

#### Generating Python files on Linux

```bash
pip install -e .
cimgen --outdir=output/python/CGMES_2.4.15_27JAN2020 --schemadir=cgmes_schema/CGMES_2.4.15_27JAN2020 --langdir=python --cgmes_version=cgmes_v2_4_15
```

alternatively, you can leverage `Makefile`:

```bash
pip install -e .
#unset BUILD_IN_DOCKER # if you previously set to use docker
#export SCHEMA=CGMES_3.0.0 # to use CGMES 3.0.0
make python
```

#### Generating Python files in a Docker container

```bash
docker build --tag cimgen --file Dockerfile .
docker run --volume "$(pwd)/output:/output" cimgen --outdir=/output/python/CGMES_2.4.15_27JAN2020 --schemadir=/cimgen/cgmes_schema/CGMES_2.4.15_27JAN2020 --langdir=python --cgmes_version=cgmes_v2_4_15
```

alternatively, you can leverage `Makefile`:

```bash
export BUILD_IN_DOCKER=true
#export SCHEMA=CGMES_3.0.0 to use CGMES 3.0.0
make python
```

### Generating Modern Python (i.e. PyDantic based dataclasses) files

#### Generating Modern Python files on Linux

```bash
pip install -e .
cimgen --outdir=output/modernpython/CGMES_2.4.15_27JAN2020 --schemadir=cgmes_schema/CGMES_2.4.15_27JAN2020 --langdir=modernpython --cgmes_version=cgmes_v2_4_15
```

`outdir` can be set to whichever absolute path you wish to create the files in.

alternatively, you can leverage `Makefile`:

```bash
pip install -e .
#unset BUILD_IN_DOCKER # if you previously set to use docker
#export SCHEMA=CGMES_3.0.0 # to use CGMES 3.0.0
make modernpython
```

#### Generating Modern Python files in a Docker container

```bash
docker build --tag cimgen --file Dockerfile .
docker run --volume "$(pwd)/output:/output" cimgen --outdir=/output/modernpython/CGMES_2.4.15_27JAN2020 --schemadir=/cimgen/cgmes_schema/CGMES_2.4.15_27JAN2020 --langdir=modernpython --cgmes_version=cgmes_v2_4_15
```

alternatively, you can leverage `Makefile`:

```bash
export BUILD_IN_DOCKER=true
#export SCHEMA=CGMES_3.0.0 to use CGMES 3.0.0
make modernpython
```
## Zaphiro notes
Zaphiro extends CGMES by introducing custom classes and also by providing subclasses with identical names to CGMES classes.
CIMGEN currently cannot properly differentiate CGMES classes from Zaphiro subclasses automatically, so manual post-processing is required.

### Input Schema Folder
To generate Zaphiro-aware classes, point schemadir to a directory containing:

- The standard CGMES RDF schemas
- Zaphiro’s custom RDF schemas

Example:

    cimgen --outdir=output/sqlalchemy/test --schemadir=cgmes_schema/cgmes_plus_zaphiro --langdir=sqlalchemy --cgmes_version=cgmes_v3_0_0

### After Generation: What You Must Fix Manually
CIMGEN will tend to generate objects like:

#### Step 1 — Separate Zaphiro Models
CIMGEN outputs all SQLAlchemy models in a single file.
You must:
- Identify Zaphiro-specific classes
- Move them into a dedicated Zaphiro models file (keeps our extensions cleanly separated from CGMES standard classes)

#### Step 2 — Rename Zaphiro Subclasses to Avoid Import Ambiguity

To avoid confusion between cgmes's Substation and zaphiro's Substation, rename Zaphiro extensions to use a prefix:
``ZaphiroSubstation``

And update SQLAlchemy metadata by adding prefix ``zaphiro_``:
- ``__tablename__``
- ``ForeignKey`` definitions
- ``polymorphic_identity``

```
class ZaphiroSubstationClass(...):
    __tablename__ = "zaphiro_substation"
    __mapper_args__ = {"polymorphic_identity": "zaphiro_substation"}

```
#### Step 3 — Fix Subclasses with the Same Name as CGMES Classes

For example: our custom Substation, Terminal, etc.

You must:
1. Ensure inheritance is correct
2. Remove inherited attributes that belong to the CGMES parent and only keep Zaphiro-specific fields.
CIMGEN will likely generate
```
class ZaphiroSubstationClass(EquipmentContainer):
```

While the correct model is:
```
class ZaphiroSubstationClass(SubstationClass): # Parent SubstationClass is from CGMES
```

#### Step 4 — Review Relationships (Critical)

Zaphiro classes often introduce new relationships that can cause:
- circular imports
- SQLAlchemy circular dependencies
- invalid backrefs
- repeated or conflicting FK definitions

You must review:
- all relationship() definitions
- foreign keys
- parent/child direction
- mapper arguments

This step requires domain knowledge + SQLAlchemy experience.

## License

This project is released under the terms of the [Apache 2.0 license](./LICENSE).

## Publications

If you are using CIMgen for your research, please cite the following paper in
your publications:

Dinkelbach, J., Razik, L., Mirz, M., Benigni, A., Monti, A.: Template-based
generation of programming language specific code for smart grid modelling
compliant with CIM and CGMES.
J. Eng. 2023, 1-13 (2022). [https://doi.org/10.1049/tje2.12208](https://doi.org/10.1049/tje2.12208)
