from graphene_django.views import GraphQLView

from .context import GraphQLContext


class CustomGraphQLView(GraphQLView):

    def get_context(self, request):
        return GraphQLContext()


class TracedGraphQLView(GraphQLView):
    """Keep the normal request context and annotate GraphQL failures at HTTP 200."""

    def execute_graphql_request(
        self, request, data, query, variables, operation_name, show_graphiql=False,
    ):
        from config.telemetry import span
        from graphql import GraphQLError, get_operation_ast, parse

        with span("graphql.execute") as current:
            if current is not None and query:
                try:
                    operation = get_operation_ast(parse(query), operation_name)
                except GraphQLError:
                    operation = None
                if operation is not None:
                    operation_type = operation.operation.value
                    name = operation.name.value if operation.name else "anonymous"
                    current.update_name(f"graphql.{operation_type} {name}")
                    current.set_attribute("graphql.operation.type", operation_type)
                    current.set_attribute("graphql.operation.name", name)
            result = super().execute_graphql_request(
                request, data, query, variables, operation_name, show_graphiql,
            )
            if current is not None and result is not None and result.errors:
                from opentelemetry.trace import StatusCode
                current.set_status(StatusCode.ERROR)
                current.set_attribute("graphql.error.count", len(result.errors))
            return result
