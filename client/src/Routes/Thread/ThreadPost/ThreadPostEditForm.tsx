import { Trans, t } from "@lingui/macro"
import { I18n } from "@lingui/react"
import React from "react"
import * as Yup from "yup"
import { useSettingsContext } from "../../../Context"
import {
  ButtonPrimary,
  ButtonSecondary,
  CardAlert,
  CardBody,
  CardFooter,
  Form,
} from "../../../UI"
import { IPost } from "../Thread.types"
import ThreadPostLoader from "./ThreadPostLoader"
import ThreadPostRootError from "./ThreadPostRootError"
import useEditPostMutation from "./useEditPostMutation"

interface IThreadPostEditFormProps {
  post: IPost
  testLoading?: boolean
  close: () => void
}

interface IFormValues {
  markup: string
}

const Editor = React.lazy(() => import("../../../Editor"))

const ThreadPostEditForm: React.FC<IThreadPostEditFormProps> = ({
  testLoading,
  post,
  close,
}) => {
  const { postBodyMinLength } = useSettingsContext()

  const EditThreadPostSchema = Yup.object().shape({
    markup: Yup.string()
      .required("value_error.missing")
      .min(postBodyMinLength, "value_error.any_str.min_length"),
  })

  const { data, loading, editPost, error: graphqlError } = useEditPostMutation(
    post
  )

  if (testLoading) return <ThreadPostLoader />

  return (
    <React.Suspense fallback={<ThreadPostLoader />}>
      <Form<IFormValues>
        className="post-edit-form"
        id={"thread_post_edit_form_" + post.id}
        defaultValues={{ markup: post.body.text }}
        disabled={loading}
        validationSchema={EditThreadPostSchema}
        onSubmit={async ({ clearError, setError, data: { markup } }) => {
          clearError()

          try {
            const result = await editPost(markup)
            const { errors } = result.data?.editPost || {}

            if (errors) {
              errors?.forEach(({ location, type, message }) => {
                const field = location.join(".") as "markup"
                setError(field, type, message)
              })
            } else {
              close()
            }
          } catch (error) {
            // do nothing when editPost throws
            return
          }
        }}
      >
        <ThreadPostRootError
          graphqlError={graphqlError}
          dataErrors={data?.editPost.errors}
        >
          {({ message }) => <CardAlert>{message}</CardAlert>}
        </ThreadPostRootError>
        <CardBody className="post-edit-form-body">
          <Editor name="markup" disabled={loading} />
        </CardBody>
        <CardFooter className="post-edit-form-footer">
          <I18n>
            {({ i18n }) => (
              <ButtonSecondary
                text={<Trans id="cancel">Cancel</Trans>}
                disabled={loading}
                onClick={() => {
                  const confirm = window.confirm(
                    i18n._(
                      t(
                        "moderation.edit_post_cancel_prompt"
                      )`Are you sure you want to abandon changes?`
                    )
                  )
                  if (confirm) close()
                }}
                small
              />
            )}
          </I18n>
          <ButtonPrimary
            text={<Trans id="moderation.edit_post">Save changes</Trans>}
            loading={loading}
            small
          />
        </CardFooter>
      </Form>
    </React.Suspense>
  )
}

export default ThreadPostEditForm
