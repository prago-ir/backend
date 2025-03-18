from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS, connection
from django.db.utils import OperationalError, ProgrammingError
import getpass
import sys


class Command(BaseCommand):
    help = 'Create a superuser with either email or phone'
    requires_migrations_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            dest='username',
            default=None,
            help='Specifies the username for the superuser.',
        )
        parser.add_argument(
            '--email',
            dest='email',
            default=None,
            help='Specifies the email for the superuser.',
        )
        parser.add_argument(
            '--phone',
            dest='phone',
            default=None,
            help='Specifies the phone number for the superuser.',
        )
        parser.add_argument(
            '--password',
            dest='password',
            default=None,
            help='Specifies the password for the superuser. If not provided, will prompt for it.',
        )
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false',
            dest='interactive',
            default=True,
            help='Tells Django to NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '--database',
            action='store',
            dest='database',
            default=DEFAULT_DB_ALIAS,
            help='Specifies the database to use.',
        )

    def get_input_data(self, field_name, message, default=None):
        """
        Override this method if you want to customize data inputs or validation exceptions.
        """
        raw_value = input(message)
        if default and raw_value == '':
            raw_value = default
        return raw_value

    def get_password_input(self, message):
        """Get password with getpass to hide input."""
        return getpass.getpass(message)

    def handle(self, *args, **options):
        UserModel = get_user_model()
        username = options.get('username')
        email = options.get('email')
        phone = options.get('phone')
        password = options.get('password')
        interactive = options.get('interactive')
        database = options.get('database')
        verbosity = options.get('verbosity')

        # If non-interactive mode, ensure we have required fields
        if not interactive:
            if not password:
                raise CommandError('You must use --password with --noinput.')
            if not (email or phone):
                raise CommandError('Either --email or --phone must be provided when using --noinput.')
            if hasattr(UserModel, 'USERNAME_FIELD') and not username and UserModel.USERNAME_FIELD != 'email':
                raise CommandError(f'You must specify --{UserModel.USERNAME_FIELD} with --noinput.')

        # Handle interactive mode
        if interactive:
            self.stdout.write(self.style.NOTICE('Creating a superuser account'))
            
            # Get username if required
            if hasattr(UserModel, 'USERNAME_FIELD') and UserModel.USERNAME_FIELD != 'email':
                if not username:
                    username = self.get_input_data(
                        UserModel.USERNAME_FIELD,
                        f'{UserModel.USERNAME_FIELD.capitalize()}: '
                    )
                
            # Get email if not provided
            if not email and not phone:
                while True:
                    email = self.get_input_data('email', 'Email address: ')
                    if email:
                        break
                    self.stdout.write(self.style.WARNING('Email cannot be blank if phone is not provided.'))
            
            # Get phone if not provided and email is not provided
            if not email and not phone:
                while True:
                    phone = self.get_input_data('phone', 'Phone number: ')
                    if phone:
                        break
                    self.stdout.write(self.style.WARNING('Phone cannot be blank if email is not provided.'))
            
            # Get password
            while password is None:
                password = self.get_password_input('Password: ')
                password2 = self.get_password_input('Password (again): ')
                if password != password2:
                    self.stderr.write(self.style.ERROR("Error: Your passwords didn't match."))
                    password = None
                    continue
                if password.strip() == '':
                    self.stderr.write(self.style.ERROR("Error: Blank passwords aren't allowed."))
                    password = None
                    continue

        # Prepare user data
        user_data = {}
        
        if hasattr(UserModel, 'USERNAME_FIELD'):
            user_data[UserModel.USERNAME_FIELD] = username
        
        if email:
            user_data['email'] = email
        
        if phone:
            user_data['phone'] = phone
            
        # Add password to user_data instead of setting it after creation
        user_data['password'] = password
        
        # Create the superuser
        try:
            from django.db import transaction
            
            # Use transaction to ensure we can roll back if profile creation fails
            with transaction.atomic():
                # Create user with create_superuser method directly
                user = UserModel._default_manager.db_manager(database).create_superuser(
                    **user_data
                )
                
                # Ensure Profile exists for this user
                from accounts.models import Profile
                try:
                    # Check if profile exists
                    Profile.objects.get(user=user)
                except Profile.DoesNotExist:
                    # Create profile if it doesn't exist
                    Profile.objects.create(user=user)
                
                if verbosity >= 1:
                    self.stdout.write(self.style.SUCCESS("Superuser created successfully."))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error creating superuser: {str(e)}"))
            if "no such table: accounts_profile" in str(e):
                self.stderr.write(self.style.ERROR(
                    "The Profile table doesn't exist. Run 'python manage.py migrate' first."
                ))
            raise CommandError(str(e))
