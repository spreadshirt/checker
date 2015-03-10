Checker
=======

Checker is a quality assurance tool to organize pre-release checklists. It makes it possible to
automate certain checks and gives an overview of the test status of current and previous releases.

Installation
------------

1. Create sqlite database with
   `cat schema.sql | sqlite3 /tmp/checker.db`
2. (Optional) Add pre-defined checklists to sqlite database with
   `cat checklists.sql | sqlite3 /tmp/checker.db`
3. (Optional) Add test data to sqlite database with
   `cat testdata.sql | sqlite3 /tmp/checker.db`
4. Run checker
   `python src/checker.py`
5. Open browser and go to http://127.0.0.1:5000/

Dependencies to have it running on Mac
--------------------------------------

1. Install Sqllite3
   `brew install sqlite3`
2. Install Python3
   `brew install python3`
3. Install Selenium dependency for Python
   `pip3 install selenium`
4. Install Flask dependency for Python
   `pip3 install flask`
5. Install Requests dependency for Python
   `pip3 install requests`

Usage
-----

There are four different entities:
* releases
* components
* checklists
* placeholders

A *checklist* is a list item that can have the different states *not run*, *not needed*, *passed* and *failed*. There are currently
three different types of checklists: plain, screenshots and jenkins.

A *plain checklist* is just a text that explains a manual process. You can also add HTML tags to create a list of steps etc.

A *screenshots checklist* creates screenshots of webpages of the tested system (actual) and the stable system (expected).
It helps to manual check for layout bugs easily.

A *jenkins checklist* is basically a link to a build job on a Jenkins build server. It shows the current state of the job.

*Components* can contain a sum of the above mentioned checklists.

*Releases* can contain a sum of component.

*Placeholders* can be used to individualize all the checklists of a release. They can be set at the creation of a
*Release* and automatically fill the spaces in the checklist configuration. They are surrounded by curly braces: \{ \}

