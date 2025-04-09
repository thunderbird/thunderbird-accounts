Tasks
--------

We use Celery (https://docs.celeryq.dev/en/stable/) to run bits of code (known as tasks) in the background.

Creating a task
===============

A task is a simple function usually located in an app's ``tasks.py`` file. It's usually prefixed with a ``@shared_task(bind=True)`` decorator which provides the task with a ``.delay`` function call.

An example of this would be:

.. code-block:: python

  # Demonstration purposes only
  import smtplib
  from email.message import EmailMessage

  # Import the shared_task decorator from celery
  from celery import shared_task

  # Apply the decorator so you can call the task with .delay
  # bind=True gives the task a self parameter.
  # See: https://docs.celeryq.dev/en/stable/userguide/tasks.html#bound-tasks for more information.
  @shared_task(bind=True)
  def send_user_an_email(self, user_email: str):

      # Demonstration purposes only
      msg = EmailMessage()
      msg.set_content('This is the email body!')
      msg['Subject'] = 'Hello World'
      msg['From'] = 'no-reply@example.org'
      msg['To'] = user_email

      s = smtplib.SMTP('localhost')
      s.send_message(msg)
      s.quit()

      return

This task takes in a user email and sends them a 'Hello World' email sometime in the future. The timing of when this is sent out depends on what queue a task is in, how full that queue is, and if a worker is scheduled to work on that queue.

Using a task
===============

In order to call a task you simply import and use it like so:

.. code-block:: python

  # Import the tasks module and not the individual task
  from thunderbird_accounts.client import tasks

  def some_function():
    # Run this code in the backend
    user_email = 'melissa@example.org'
    tasks.my_task.delay(user_email)

It's important to import the tasks module and not the individual function, otherwise it will be harder to mock / patch in tests.

Testing a task
==============

While unit testing is pretty simple, you may run into a situation where you need to do a request call against a view that eventually calls a task. In order to prevent the task from being queued or fired you can patch it. This gives us the additional benefit of making sure it gets called when we want it to.

.. code-block:: python

    def test_some_function():
      # You can use ``with`` or decorate the function / class with @patch(...).
      # If you use the decorator you will need to adjust the function definition to
      # ``def test_some_function(email_task_mock)``.
      with patch('thunderbird_accounts.client.tasks.send_user_an_email', Mock()) as email_task_mock:
          # Your remote request to the endpoint which contains some_function()
          response = self.client.post('http://testserver/some-function')

          # Ensure the task itself wasn't called
          email_task_mock.assert_not_called()
          # Ensure the task's delay function was called
          email_task_mock.delay.assert_called_once()

