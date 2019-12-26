from typing import Dict, List, Tuple

from ariadne import MutationType, convert_kwargs_to_snake_case
from graphql import GraphQLResolveInfo
from pydantic import PositiveInt, create_model

from ...errors import ErrorsList
from ...hooks import (
    move_threads_hook,
    move_threads_input_hook,
    move_threads_input_model_hook,
)
from ...loaders import load_threads, store_threads
from ...threads.move import move_threads
from ...types import (
    AsyncValidator,
    GraphQLContext,
    MoveThreadsInput,
    MoveThreadsInputModel,
    Thread,
)
from ...utils.lists import clear_list
from ...validation import (
    CategoryExistsValidator,
    CategoryIsOpenValidator,
    CategoryModeratorValidator,
    ThreadCategoryValidator,
    ThreadExistsValidator,
    ThreadsBulkValidator,
    UserIsAuthorizedRootValidator,
    bulkactionidslist,
    validate_data,
    validate_model,
)
from ..errorhandler import error_handler


move_threads_mutation = MutationType()


@move_threads_mutation.field("moveThreads")
@convert_kwargs_to_snake_case
@error_handler
async def resolve_move_threads(
    _, info: GraphQLResolveInfo, *, input: dict  # pylint: disable=redefined-builtin
):
    input_model = await move_threads_input_model_hook.call_action(
        create_input_model, info.context
    )
    cleaned_data, errors = validate_model(input_model, input)

    if cleaned_data.get("threads"):
        threads = clear_list(await load_threads(info.context, cleaned_data["threads"]))
    else:
        threads = []

    if cleaned_data:
        validators: Dict[str, List[AsyncValidator]] = {
            "threads": [
                ThreadsBulkValidator(
                    [
                        ThreadExistsValidator(info.context),
                        ThreadCategoryValidator(
                            info.context, CategoryModeratorValidator(info.context)
                        ),
                    ]
                )
            ],
            "category": [
                CategoryExistsValidator(info.context),
                CategoryIsOpenValidator(info.context),
            ],
            ErrorsList.ROOT_LOCATION: [UserIsAuthorizedRootValidator(info.context)],
        }
        cleaned_data, errors = await move_threads_input_hook.call_action(
            validate_input_data, info.context, validators, cleaned_data, errors
        )

    if errors:
        return {"errors": errors, "threads": threads or None}

    threads = await move_threads_hook.call_action(
        move_threads_action, info.context, cleaned_data
    )

    return {"threads": threads}


async def create_input_model(context: GraphQLContext) -> MoveThreadsInputModel:
    return create_model(
        "MoveThreadsInputModel",
        threads=(bulkactionidslist(PositiveInt, context["settings"]), ...),
        category=(PositiveInt, ...),
    )


async def validate_input_data(
    context: GraphQLContext,
    validators: Dict[str, List[AsyncValidator]],
    data: MoveThreadsInput,
    errors: ErrorsList,
) -> Tuple[MoveThreadsInput, ErrorsList]:
    return await validate_data(data, validators, errors)


async def move_threads_action(
    context: GraphQLContext, cleaned_data: MoveThreadsInput
) -> List[Thread]:
    threads = cleaned_data["threads"]
    threads = await move_threads(threads, cleaned_data["category"])
    store_threads(context, threads)

    return threads
