/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "ScanningSession.h"
#include "ResultViewer.h"
#include "Exceptions.h"

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <scap_ds.h>
#include <oscap_error.h>
#include <oscap.h>
}

#include <cassert>
#include <ctime>
#include <QFileInfo>
#include <QXmlQuery>
#include <QXmlItem>
#include <QXmlResultItems>
#include <QXmlNodeModelIndex>

ScanningSession::ScanningSession():
    mSession(0),
    mTailoring(0),

    mSessionDirty(false),
    mTailoringUserChanges(false)
{
    mTailoringFile.setFileTemplate(QDir::temp().filePath("tailoring-xccdf.xml"));
    mTailoringFile.setAutoRemove(true);
}

ScanningSession::~ScanningSession()
{
    closeFile();
}

struct xccdf_session* ScanningSession::getXCCDFSession() const
{
    reloadSession();
    return mSession;
}

void ScanningSession::openFile(const QString& path)
{
    if (mSession)
        closeFile();

    mSession = xccdf_session_new(path.toUtf8().constData());
    if (!mSession)
        throw ScanningSessionException(
            QString("Failed to create session for '%1'. OpenSCAP error message:\n%2").arg(path).arg(QString::fromUtf8(oscap_err_desc())));

    mSessionDirty = true;
    mTailoringUserChanges = false;

    // set default profile after opening, this ensures that xccdf_policy can be returned
    setProfileID(QString());
}

void ScanningSession::closeFile()
{
    const QString oldOpenedFile = mSession ? xccdf_session_get_filename(mSession) : "";

    if (mSession)
    {
        // session "owns" mTailoring and will free it as part of xccdf_policy_model
        xccdf_session_free(mSession);

        mSession = 0;
        mTailoring = 0;

        mSessionDirty = false;
        mTailoringUserChanges = false;
    }
}

QString ScanningSession::getOpenedFilePath() const
{
    if (!fileOpened())
        return QString::null;

    return xccdf_session_get_filename(mSession);
}

inline void getDependencyClosureOfFile(const QString& filePath, QSet<QString>& targetSet)
{
    QFileInfo fileInfo(filePath);
    targetSet.insert(fileInfo.absoluteFilePath()); // insert current file
    QDir parentDir = fileInfo.dir();

    oscap_document_type_t docType;
    if (oscap_determine_document_type(filePath.toUtf8().constData(), &docType) != 0)
        return;

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
        throw ScanningSessionException(QString(
            "Can't open file '%1' when calculating opened files closure.").arg(filePath));

    if (docType == OSCAP_DOCUMENT_XCCDF)
    {
        QXmlQuery depQuery;
        depQuery.setFocus(&file);
        depQuery.setQuery("//*[local-name() = 'check-content-ref']/@href");

        if (depQuery.isValid())
        {
            QXmlResultItems result;
            depQuery.evaluateTo(&result);

            QXmlItem item(result.next());
            while (!item.isNull())
            {
                QXmlNodeModelIndex itemIdx = item.toNodeModelIndex();
                const QAbstractXmlNodeModel* model = itemIdx.model();
                const QString  relativeFileName = model->stringValue(itemIdx);
                getDependencyClosureOfFile(parentDir.absoluteFilePath(relativeFileName), targetSet);
                item = result.next();
            }

            if (result.hasError())
                throw ScanningSessionException(QString(
                    "Error encountered when running an XPath query on file '%1'. "
                    "The most likely reason is that the file is not a valid XCCDF file. "
                    "If you think this is not the case, please report this bug!").arg(filePath));
        }
    }
    else if (docType == OSCAP_DOCUMENT_OVAL_DEFINITIONS)
    {
        // TODO
    }
    else if (docType == OSCAP_DOCUMENT_SDS)
    {
        // NOOP, source datastream should have everything inbuilt
    }
}

QSet<QString> ScanningSession::getOpenedFilesClosure() const
{
    QSet<QString> ret;
    getDependencyClosureOfFile(getOpenedFilePath(), ret);
    return ret;
}

QDir ScanningSession::getCommonAncestorDirectory(const QSet<QString>& paths)
{
    if (paths.isEmpty())
        return QDir::root();

    QSet<QString>::const_iterator it = paths.begin();
    QDir commonAncestor = QFileInfo(*it).dir();
    while (it != paths.end())
    {
        QDir parentDir = QFileInfo(*it).dir();

        while (!parentDir.absolutePath().startsWith(commonAncestor.absolutePath()))
            commonAncestor.cdUp();

        ++it;
    }

    return commonAncestor;
}

void ScanningSession::copyOrReplace(const QString& from, const QString& to)
{
    // QFile::copy does not overwrite, if the target file already exist
    // we have to remove it.
    if (QFile::exists(to))
    {
        if (!QFile::remove(to))
            throw ScanningSessionException(QString(
                "Could not replace '%1'. Make sure you have permissions to "
                "overwrite the files.").arg(to));
    }

    if (!QFile::copy(from, to))
        throw ScanningSessionException(QString(
            "Could not save file to '%1' (copying '%2' to '%1'). Make sure you have permissions to "
            "write to that directory").arg(to).arg(from));
}

QSet<QString> ScanningSession::saveOpenedFilesClosureToDir(const QDir& dir)
{
    QSet<QString> ret; // we insert files we have saved to this set
    const QSet<QString> closure = getOpenedFilesClosure();

    QDir commonAncestor = getCommonAncestorDirectory(closure);
    if (commonAncestor.isRoot())
        throw ScanningSessionException(
            "Common ancestor of opened files closure is the root directory. "
            "This is likely not expected. I refuse to save the closure!");

    for (QSet<QString>::const_iterator it = closure.begin(); it != closure.end(); ++it)
    {
        const QString& currentFilePath = *it;
        const QString currentFileRelPath = commonAncestor.relativeFilePath(currentFilePath);

        const QFileInfo targetFile(dir, currentFileRelPath);
        const QString targetFilePath = targetFile.absoluteFilePath();

        if (!dir.mkpath(targetFile.dir().absolutePath()))
            throw ScanningSessionException(QString(
                "Can't make directory for file '%1' (directory = '%2'). Therefore "
                "the file can't be saved.").arg(targetFilePath).arg(targetFile.dir().absolutePath()));

        copyOrReplace(currentFilePath, targetFilePath);

        // Sanity test, this should always check out if the copy was successful.
        assert(targetFile.exists());
        ret.insert(targetFilePath);
    }

    // Tailoring file is a special case (if it's in temp directory it would break closure)
    // we add it to the target dir which seems to fit most use cases
    if (hasTailoring())
    {
        QFileInfo tailoringFile(getTailoringFilePath());
        assert(tailoringFile.exists());

        // Intentionally use a hardcoded filename because tailoring filename will
        // most likely be a garbled temporary filename ("qt_temp.XXXX")
        QFileInfo targetFile(dir, "tailoring-xccdf.xml");

        copyOrReplace(tailoringFile.absoluteFilePath(), targetFile.absoluteFilePath());

        assert(targetFile.exists());
        ret.insert(targetFile.absoluteFilePath());
    }

    return ret;
}

bool ScanningSession::fileOpened() const
{
    return mSession != 0;
}

bool ScanningSession::isSDS() const
{
    if (!fileOpened())
        return false;

    reloadSession();
    return xccdf_session_is_sds(mSession);
}

void ScanningSession::setDatastreamID(const QString& datastreamID)
{
    if (!isSDS())
        throw ScanningSessionException(
            "Can't set datastream ID in scanning session unless opened file is a source datastream");

    if (datastreamID.isEmpty())
        xccdf_session_set_datastream_id(mSession, 0);
    else
        xccdf_session_set_datastream_id(mSession, datastreamID.toUtf8().constData());

    mSessionDirty = true;
}

QString ScanningSession::getDatastreamID() const
{
    if (!isSDS())
        throw ScanningSessionException(
            "Can't get datastream ID in scanning session unless opened file is a source datastream");

    return xccdf_session_get_datastream_id(mSession);
}

void ScanningSession::setComponentID(const QString& componentID)
{
    if (!isSDS())
        throw ScanningSessionException(
            "Can't set datastream ID in scanning session unless opened file is a source datastream");

    if (componentID.isEmpty())
        xccdf_session_set_component_id(mSession, 0);
    else
        xccdf_session_set_component_id(mSession, componentID.toUtf8().constData());

    mSessionDirty = true;
}

QString ScanningSession::getComponentID() const
{
    if (!isSDS())
        throw ScanningSessionException(
            "Can't get component ID in scanning session unless opened file is a source datastream");

    return xccdf_session_get_component_id(mSession);
}

void ScanningSession::resetTailoring()
{
    if (!fileOpened())
        return;

    xccdf_session_set_user_tailoring_cid(mSession, 0);
    xccdf_session_set_user_tailoring_file(mSession, 0);

    mTailoring = 0;

    mSessionDirty = true;
    mTailoringUserChanges = false;
}

void ScanningSession::setTailoringFile(const QString& tailoringFile)
{
    if (!fileOpened())
        return;

    xccdf_session_set_user_tailoring_cid(mSession, 0);
    xccdf_session_set_user_tailoring_file(mSession, tailoringFile.toUtf8().constData());

    mTailoring = 0;

    mSessionDirty = true;
    mTailoringUserChanges = false;
}

void ScanningSession::setTailoringComponentID(const QString& componentID)
{
    if (!fileOpened())
        return;

    xccdf_session_set_user_tailoring_file(mSession, 0);
    xccdf_session_set_user_tailoring_cid(mSession, componentID.toUtf8().constData());

    mTailoring = 0;

    mSessionDirty = true;
    mTailoringUserChanges = false;
}

void ScanningSession::saveTailoring(const QString& path)
{
    ensureTailoringExists();

    if (xccdf_tailoring_get_benchmark_ref(mTailoring) == NULL)
    {
        // we don't set the absolute path as benchmark ref to avoid revealing directory structure
        QFileInfo fileInfo(getOpenedFilePath());
        xccdf_tailoring_set_benchmark_ref(mTailoring, fileInfo.fileName().toUtf8().constData());
    }

    struct xccdf_benchmark* benchmark = getXCCDFInputBenchmark();
    if (xccdf_tailoring_export(
        mTailoring,
        path.toUtf8().constData(),
        xccdf_benchmark_get_schema_version(benchmark)
    ) != 1) // 1 is actually success here, big inconsistency in openscap API :(
    {
        throw ScanningSessionException(
            QString("Exporting tailoring to '%1' failed! Details follow:\n%2").arg(path).arg(QString::fromUtf8(oscap_err_desc()))
        );
    }
}

QString ScanningSession::getTailoringFilePath()
{
    if (mTailoringFile.isOpen())
        mTailoringFile.close();

    mTailoringFile.open();
    mTailoringFile.close();

    const QString fileName = mTailoringFile.fileName();
    saveTailoring(fileName);

    return fileName;
}

bool ScanningSession::hasTailoring() const
{
    if (!mTailoring)
        return false;

    // Tailoring with 0 profiles is invalid (and it makes no sense to send
    // such profile to the scanner, it wouldn't affect the scan in any way)
    struct xccdf_profile_iterator* it = xccdf_tailoring_get_profiles(mTailoring);
    const bool ret = xccdf_profile_iterator_has_more(it);
    xccdf_profile_iterator_free(it);

    return ret;
}

void ScanningSession::setProfileID(const QString& profileID)
{
    if (!fileOpened())
        throw ScanningSessionException(QString("File hasn't been opened, can't set profile to '%1'").arg(profileID));

    reloadSession();

    if (!xccdf_session_set_profile_id(mSession, profileID.isEmpty() ? NULL : profileID.toUtf8().constData()))
        throw ScanningSessionException(QString("Failed to set profile ID to '%1'. oscap error: %2").arg(profileID).arg(QString::fromUtf8(oscap_err_desc())));
}

QString ScanningSession::getProfileID() const
{
    if (!fileOpened())
        throw ScanningSessionException(QString("File hasn't been opened, can't get profile ID"));

    reloadSession();

    return xccdf_session_get_profile_id(mSession);
}

bool ScanningSession::profileSelected() const
{
    if (!fileOpened())
        return false;

    reloadSession();
    return xccdf_session_get_profile_id(mSession) != 0;
}

bool ScanningSession::isSelectedProfileTailoring() const
{
    if (!fileOpened())
        return false;

    reloadSession();

    struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(mSession);
    if (!policyModel)
        return false;

    struct xccdf_policy* policy= xccdf_session_get_xccdf_policy(mSession);
    if (!policy)
        return false;

    struct xccdf_profile* profile = xccdf_policy_get_profile(policy);
    if (!profile)
        return false;

    return xccdf_profile_get_tailoring(profile);
}


void ScanningSession::reloadSession(bool forceReload) const
{
    if (!fileOpened())
        throw ScanningSessionException(
            QString("Can't reload session, file hasn't been opened!"));

    if (mSessionDirty || forceReload)
    {
        if (xccdf_session_load(mSession) != 0)
            throw ScanningSessionException(
                QString("Failed to reload session. OpenSCAP error message:\n%1").arg(QString::fromUtf8(oscap_err_desc())));

        struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(mSession);

        // In case we didn't have any tailoring previously, lets use the one from the session.
        // Otherwise we will reuse our own tailoring instead of the session's because we may
        // already have user-made changes in it!

        if (!mTailoringUserChanges)
            mTailoring = xccdf_policy_model_get_tailoring(policyModel);
        else
            xccdf_policy_model_set_tailoring(policyModel, mTailoring);

        mSessionDirty = false;
    }
}

struct xccdf_profile* ScanningSession::tailorCurrentProfile(bool shadowed)
{
    reloadSession();

    if (!fileOpened())
        return 0;

    // create a new profile, inheriting the currently selected profile
    // or no profile if currently selected profile is the '(default)'
    struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(mSession);
    if (!policyModel)
        return 0;

    struct xccdf_profile* newProfile = xccdf_profile_new();

    struct xccdf_policy* policy= xccdf_session_get_xccdf_policy(mSession);
    struct xccdf_profile* oldProfile = policy ? xccdf_policy_get_profile(policy) : 0;

    // TODO: new profile's ID may clash with existing profile!
    if (oldProfile && xccdf_profile_get_id(oldProfile))
    {
        xccdf_profile_set_extends(newProfile, xccdf_profile_get_id(oldProfile));

        if (shadowed)
        {
            xccdf_profile_set_id(newProfile, xccdf_profile_get_id(oldProfile));
        }
        else
        {
            const QString newIdBase = QString::fromUtf8(xccdf_profile_get_id(oldProfile)) + QString("_tailored");
            QString newId = newIdBase;
            int suffix = 2;
            while (xccdf_policy_model_get_policy_by_id(policyModel, newId.toUtf8().constData()) != NULL)
                newId = QString("%1%2").arg(newIdBase).arg(suffix++);
            xccdf_profile_set_id(newProfile, newId.toUtf8().constData());
        }

        struct oscap_text_iterator* titles = xccdf_profile_get_title(oldProfile);
        while (oscap_text_iterator_has_more(titles))
        {
            struct oscap_text* oldTitle = oscap_text_iterator_next(titles);
            struct oscap_text* newTitle = oscap_text_clone(oldTitle);

            oscap_text_set_text(newTitle, (QString::fromUtf8(oscap_text_get_text(oldTitle)) + QString(" [TAILORED]")).toUtf8().constData());
            xccdf_profile_add_title(newProfile, newTitle);
        }
        oscap_text_iterator_free(titles);

        struct oscap_text_iterator* descs = xccdf_profile_get_description(oldProfile);
        while (oscap_text_iterator_has_more(descs))
        {
            struct oscap_text* oldDesc = oscap_text_iterator_next(descs );
            struct oscap_text* newDesc = oscap_text_clone(oldDesc);

            xccdf_profile_add_description(newProfile, newDesc);
        }
        oscap_text_iterator_free(descs);
    }
    else
    {
        xccdf_profile_set_id(newProfile, "xccdf_scap-workbench_profile_default_tailored");

        {
            struct oscap_text* newTitle = oscap_text_new();
            oscap_text_set_lang(newTitle, OSCAP_LANG_ENGLISH_US);
            oscap_text_set_text(newTitle, "(default) [TAILORED]");
            xccdf_profile_add_title(newProfile, newTitle);
        }
        {
            struct oscap_text* newDesc = oscap_text_new();
            oscap_text_set_lang(newDesc, OSCAP_LANG_ENGLISH_US);
            oscap_text_set_text(newDesc, "This profile doesn't inherit any other profile.");
            xccdf_profile_add_description(newProfile, newDesc);
        }
    }

    ensureTailoringExists();

    if (!xccdf_tailoring_add_profile(mTailoring, newProfile))
    {
        xccdf_profile_free(xccdf_profile_to_item((newProfile)));

        throw ScanningSessionException(
            "Failed to add a newly created profile for tailoring!");
    }

    mTailoringUserChanges = true;
    return newProfile;
}

struct xccdf_benchmark* ScanningSession::getXCCDFInputBenchmark()
{
    reloadSession();

    if (!mSession)
        return NULL;

    struct xccdf_policy_model* policyModel = xccdf_session_get_policy_model(mSession);
    return xccdf_policy_model_get_benchmark(policyModel);
}

void ScanningSession::ensureTailoringExists()
{
    reloadSession();

    if (!mTailoring)
    {
        mTailoring = xccdf_tailoring_new();
        xccdf_tailoring_set_id(mTailoring, "xccdf_scap-workbench_tailoring_default");
        xccdf_tailoring_set_version(mTailoring, "1");

        {
            time_t rawtime;
            struct tm* timeinfo;
            char buffer[80];

            time(&rawtime);
            timeinfo = localtime(&rawtime);

            strftime(buffer, 80, "%Y-%m-%dT%H:%M:%S", timeinfo);

            xccdf_tailoring_set_version_time(mTailoring, buffer);
        }

        mTailoringUserChanges = true;
        reloadSession(true);
    }
}
