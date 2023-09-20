import pathlib
import shutil
from django.contrib.auth.hashers import check_password
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from .repositories import UserRepository, ImageRepository
from PIL import Image
from decouple import config
from django.http import FileResponse
from .validate_token import validate_jwt_token

@api_view(['POST'])
def login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    user = UserRepository.get_user_by_email(email)

    if not user:
        return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

    if not check_password(password, user.password):
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def upload_image(request):
    api_base_url = config('API_BASE_URL')
    token = request.headers.get('Authorization')
    decoded_token = validate_jwt_token(token)

    if not token or not decoded_token:
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_401_UNAUTHORIZED)

    user_id = decoded_token["user_id"]
    image = request.FILES['image']
    image_path = image.name
    user = UserRepository.get_user_by_id(user_id)
    if not user:
        return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

    file_format = pathlib.Path(image_path).suffix
    file_format_without_dot = file_format.replace(".", "")
    image_path = image_path.replace(" ", "_")
    image_path = 'media/' + image_path
    image_from_db = ImageRepository.get_image_by_name(image_path)

    if image_from_db:
        return Response({"error": "This image already exists"}, status=status.HTTP_409_CONFLICT)

    ImageRepository.add_image(user, image_path, file_format_without_dot)

    with open(image_path, 'wb+') as destination:
        for chunk in image.chunks():
            destination.write(chunk)

    image_links = []

    if user.plan == "Basic":
        image_path_200px = image_path.replace(".", f"_200px.")
        shutil.copy(image_path, image_path_200px)
        file_format_without_dot = file_format.replace(".", "")
        img = Image.open(image_path_200px)
        img200px = img.resize((img.width, 200))
        img200px.save(image_path_200px, file_format_without_dot)
        ImageRepository.add_image(user, image_path_200px, file_format_without_dot)
        image200px_from_db = ImageRepository.get_image_by_name(image_path_200px)
        image_links.append({"size": 200, "link": f"{api_base_url}images/{image200px_from_db.id}"})

    return Response({"message": "Image uploaded successfully",
                     "image_links": image_links}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def show_image(request, image_id):
    image = ImageRepository.get_image_by_id(image_id)
    if not image:
        return Response({"error": "Image not found."}, status=status.HTTP_404_NOT_FOUND)
    
    image_path = image.path
    image_path = str(image_path)
    img_file = open(image_path, 'rb')

    response = FileResponse(img_file)
    return response









