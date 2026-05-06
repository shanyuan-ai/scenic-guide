from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .serializers import RegisterSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'code': 200,
                'data': {
                    'username': user.username,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'message': '注册成功'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'code': 400,
            'message': str(serializer.errors)
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')

        if not username or not password:
            return Response({
                'code': 400,
                'message': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if not user:
            return Response({
                'code': 401,
                'message': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'code': 200,
            'data': {
                'username': user.username,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'message': '登录成功'
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({
            'code': 200,
            'message': '已退出登录'
        })


class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'code': 200,
            'data': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
        })


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'code': 400,
                'message': 'Refresh Token 不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            return Response({
                'code': 200,
                'data': {
                    'access': str(token.access_token),
                },
                'message': 'Token 刷新成功'
            })
        except Exception:
            return Response({
                'code': 401,
                'message': 'Refresh Token 无效或已过期'
            }, status=status.HTTP_401_UNAUTHORIZED)