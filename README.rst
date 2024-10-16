Fetch and deploy external resource files
========================================

Sorry, this file is outdated – will be updated soon. Don't read on. Thank you.

Installation
------------

#. Install this package (as editable or from the repository) into your virtual environment.

#. Install ``invoke``,
   create a ``tasks.py`` file in the root directory of your project and insert these lines::

      from external_resources.tasks import (
              get_resources, 
              check_resource,
              deploy_resources,
              )

#. Create a file ``external_resources.yaml`` containing information about the external
   resources that you will be needing. An example is supplied with this package.

#. Create (or edit) the file ``invoke.yaml`` (in the same directory as ``tasks.py``);
   it should specify the path of your ``external_resources.yaml`` registry and
   a list of resource names and optional version specifiers (like in a requirements file).
   
   Example::
   
      external_resources:
         required:
            -  bootstrap5
            -  bootstrap5_js
            -  htmx ~= 1.7
            -  lineawesome13 ~= 1.3
         config_file: external_resources.yaml
         dir_name: static_external

   The path to the ``config_file`` can either be an absolute path or relative to the
   directory of ``invoke.yaml``.
   
   The ``dir_name`` option should point to a directory where the external resources
   will be installed (on your local host); depending on the kind of the resource they
   will go into subdirectories ``css``, ``js``, or ``fonts``.

#. The invoke command ::
   
      inv get-resources
   
   will try to download the resources specified as ``required`` into the ``dir_name``
   target directory.
   
   If the integrity check code for a resource is not known, the command ::
   
      inv check-resource NAME
   
   will calculate and display this code which then can be pasted into the registry
   to make sure the correct file was retrieved on a later download.
   
   With ::
   
      inv deploy-resources
   
   the resources from the local ``dir_name`` directory (and its subdirectories) will
   be rsync'ed to the target host specified by the ``target`` option in ``invoke.yaml``.
