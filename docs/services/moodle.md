# Moodle
Moodle is an open source Learning Management System (LMS) widely used
in educational settings to organize, deliver, and track online
courses. In Tectonic, Moodle can be deployed as a service in order to
enhance the cyber range with supplementary learning resources such as
guides, theoretical content, quizzes, forums, multimedia and many
more.

### Course creation

The main resource in Moodle is a course. To create a course, follow these steps:

1. Log in with the administrator account (credentials???).
2. Click Site administration.
3. Click the Courses tab.
4. Click Add a new course.
5. Add your course details.
6. Click Save and display.
7. Click Proceed to course content to add your teaching materials.

For more information, consult the [Moodle documentation](https://docs.moodle.org/501/en/Create_a_course).

### Add course content

Once the course is created, content must be added. There are different
types of content, such as quizzes, presentations, documents, and more.
To add content, follow these steps:

1. Log in as an administrator or teacher and go into the course.
2. Toggle Edit mode top right.
3. To add files such as documents or presentations, drag and drop them from your desktop.
4. To add other activities, click the link Add an activity or resource wherever you want to add it.
5. Choose an item and double click to add it.

For more information, consult the [Moodle documentation](https://docs.moodle.org/501/en/Add_course_content).

### Course backup

Once the courses have been created, a backup of each one must be made,
following these steps:

1. Go into the course.
2. From Course navigation > More > Course reuse, select 'Backup'.
3. Initial settings - Select activities, blocks, filters and other items as required then click the Next button. Users with appropriate permissions, such as administrators and managers, can choose whether to include users, anonymize user information, or include user role assignments, groups, groupings, user files, comments, user completion details, course logs and grade history in the backup.
4. Schema settings - Select/deselect specific items to include in backup, then click the Next button.
5. If desired, select specific types of activity to be backed up by clicking the link 'Show type options'.
6. Confirmation and review - Check that everything is as required, using the Previous button if necessary, otherwise click the 'Perform backup' button.
7. Complete - Click the Continue button.

Do not include users when making the backup.

For more information, consult the [Moodle documentation](https://docs.moodle.org/501/en/Course_backup).

Once the course backup is created, download the `mbz` file into a
`moodle` directory inside the scenario specification. Next time the
scenario is deployed, tectonic will automatically restore the contents
of the course and create and enroll users for each trainee.

