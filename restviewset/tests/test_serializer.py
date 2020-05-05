from exlib.rest.serializers import Serializer, ModelSerializer
from app.user.models import User
from flask_restplus import fields


class UsersSerializer(ModelSerializer):
    id = fields.Integer
    name = fields.String

    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'is_admin')


def test():
    user = User.select().first()
    print(UsersSerializer(user).data)


if __name__ == '__main__':
    print(UsersSerializer().fields)
    print(UsersSerializer.fields)
    test()
