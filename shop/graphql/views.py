from graphene_django.views import GraphQLView

from .context import GraphQLContext


class CustomGraphQLView(GraphQLView):

    def get_context(self, request):
        return GraphQLContext()