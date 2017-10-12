#include "RemediationRoleSaver.h"

void RemediationSaverBase::SelectFilenameAndSaveRole()
{
    const QString filename = QFileDialog::getSaveFileName(mParentWindow,
        mSaveMessage.toUtf8(),
        QString("%1.%2").arg(guessFilenameStem()).arg(mFiletypeExtension),
        mFiletypeTemplate.arg(mFiletypeExtension), 0
#ifndef SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS
        , QFileDialog::DontUseNativeDialog
#endif
    );

    if (filename.isEmpty())
        return;

    int result = SaveToFile(filename);
    if (result == 0)
    {
        // TODO: if OK
    }
    else
    {
        // TODO: if not OK
    }
}

int RemediationSaverBase::SaveToFile(const QString& filename)
{
    QFile outputFile(filename);
    outputFile.open(QIODevice::WriteOnly);
    struct xccdf_session* session = mScanningSession->getXCCDFSession();
    struct xccdf_policy* policy = xccdf_session_get_xccdf_policy(session);
    int result = xccdf_policy_generate_fix(policy, NULL, mFixTemplate.toUtf8(), outputFile.handle());
    outputFile.close();
    return result;
}

QString RemediationSaverBase::guessFilenameStem()
{
    // TODO: Add guess that uses benchmark and profile names
    return QString("remediation");
}
