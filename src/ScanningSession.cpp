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
#include "APIHelpers.h"

extern "C" {
#include <xccdf_policy.h>
#include <xccdf_session.h>
#include <scap_ds.h>
#include <oscap.h>
#include <oscap_error.h>
}

#include <cassert>
#include <ctime>
#include <QFileInfo>
#include <QBuffer>
#include <QXmlQuery>
#include <QXmlItem>
#include <QXmlResultItems>
#include <QXmlNodeModelIndex>

ScanningSession::ScanningSession():
    mSession(0),
    mTailoring(0),

    mSkipValid(false),
    mSessionDirty(false),
    mTailoringUserChanges(false)
{
    mTailoringFile.setAutoRemove(true);
}

ScanningSession::~ScanningSession()
{
    closeFile();
}

void ScanningSession::setSkipValid(bool skipValid)
{
    mSkipValid = skipValid;

    if (mSession)
        xccdf_session_set_validation(mSession, mSkipValid, false);
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

    const QFileInfo pathInfo(path);

    // We have to make sure that we *ALWAYS* open the session by absolute
    // path. oscap local won't be run from the same directory from where
    // SCAP Workbench is run
    mSession = xccdf_session_new(pathInfo.absoluteFilePath().toUtf8().constData());
    if (!mSession)
        throw ScanningSessionException(
            QString("Failed to create session for '%1'. OpenSCAP error message:\n%2").arg(path).arg(oscapErrDesc()));

    xccdf_session_set_validation(mSession, mSkipValid, false);

    mSessionDirty = true;
    mTailoringUserChanges = false;

    // set default profile after opening, this ensures that xccdf_policy can be returned
    setProfile(QString());
}

void ScanningSession::closeFile()
{
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
        return QString("");

    // we always open the session with absolute file path
    // therefore this is guaranteed to be absolute
    return xccdf_session_get_filename(mSession);
}

inline void getDependencyClosureOfFile(const QString& filePath, QSet<QString>& targetSet)
{
    QFileInfo fileInfo(filePath);
    targetSet.insert(fileInfo.absoluteFilePath()); // insert current file
    QDir parentDir = fileInfo.dir();

    struct oscap_source* source = oscap_source_new_from_file(filePath.toUtf8().constData());

    oscap_document_type_t docType = oscap_source_get_scap_type(source);

    if (docType == OSCAP_DOCUMENT_UNKNOWN)
        return;

    char* rawBuffer;
    size_t rawSize;
    if (oscap_source_get_raw_memory(source, &rawBuffer, &rawSize) != 0)
        throw ScanningSessionException(QString(
            "Can't get raw data of file '%1' when calculating opened files closure.").arg(filePath));

    QBuffer buffer;
    buffer.setData(rawBuffer, rawSize);
    free(rawBuffer);

    if (docType == OSCAP_DOCUMENT_XCCDF)
    {
        QXmlQuery depQuery;
        depQuery.setFocus(&buffer);
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
        const QFileInfo tailoringFile(getTailoringFilePath());
        assert(tailoringFile.exists());

        // Intentionally use a hardcoded filename because tailoring filename will
        // most likely be a garbled temporary filename ("qt_temp.XXXX")
        const QFileInfo targetFile(dir, "tailoring-xccdf.xml");

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
    if (datastreamID == getDatastreamID())
        return;

    resetTailoring();

    if (datastreamID.isEmpty())
        xccdf_session_set_datastream_id(mSession, 0);
    else
        xccdf_session_set_datastream_id(mSession, datastreamID.toUtf8().constData());

    mSessionDirty = true;
}

QString ScanningSession::getDatastreamID() const
{
    return QString::fromUtf8(xccdf_session_get_datastream_id(mSession));
}

void ScanningSession::setComponentID(const QString& componentID)
{
    if (componentID == getComponentID())
        return;

    resetTailoring();

    if (componentID.isEmpty())
        xccdf_session_set_component_id(mSession, 0);
    else
        xccdf_session_set_component_id(mSession, componentID.toUtf8().constData());

    mSessionDirty = true;
}

QString ScanningSession::getComponentID() const
{
    return QString::fromUtf8(xccdf_session_get_component_id(mSession));
}

QString ScanningSession::getBenchmarkTitle() const
{
    if (!fileOpened())
        return QString("");

    struct xccdf_policy_model* pmodel = xccdf_session_get_policy_model(mSession);
    struct xccdf_benchmark* benchmark = xccdf_policy_model_get_benchmark(pmodel);
    struct xccdf_policy* policy= xccdf_session_get_xccdf_policy(mSession);

    return oscapItemGetReadableTitle(xccdf_benchmark_to_item(benchmark), policy);
}

void ScanningSession::resetTailoring()
{
    if (!fileOpened())
        return;

    mTailoring = 0;

    // nothing to reset if these conditions are met
    if (!mTailoringUserChanges && mUserTailoringCID.isEmpty() && mUserTailoringFile.isEmpty())
        return;

    xccdf_session_set_user_tailoring_cid(mSession, 0);
    mUserTailoringCID = "";
    xccdf_session_set_user_tailoring_file(mSession, 0);
    mUserTailoringFile = "";

    mSessionDirty = true;
    mTailoringUserChanges = false;
}

void ScanningSession::setTailoringFile(const QString& tailoringFile)
{
    if (!fileOpened())
        return;

    // nothing to change if these conditions are met
    if (!mTailoringUserChanges && mUserTailoringCID.isEmpty() && mUserTailoringFile == tailoringFile)
        return;

    mTailoring = 0;

    xccdf_session_set_user_tailoring_cid(mSession, 0);
    mUserTailoringCID = "";
    xccdf_session_set_user_tailoring_file(mSession, tailoringFile.toUtf8().constData());
    mUserTailoringFile = tailoringFile;

    mSessionDirty = true;
    mTailoringUserChanges = false;
}

void ScanningSession::setTailoringComponentID(const QString& componentID)
{
    if (!fileOpened())
        return;

    // nothing to change if these conditions are met
    if (!mTailoringUserChanges && mUserTailoringCID == componentID && mUserTailoringFile.isEmpty())
        return;

    mTailoring = 0;

    xccdf_session_set_user_tailoring_file(mSession, 0);
    mUserTailoringFile = "";
    xccdf_session_set_user_tailoring_cid(mSession, componentID.toUtf8().constData());
    mUserTailoringCID = componentID;

    mSessionDirty = true;
    mTailoringUserChanges = false;
}

void ScanningSession::saveTailoring(const QString& path, bool userFile)
{
    ensureTailoringExists();

    if (xccdf_tailoring_get_benchmark_ref(mTailoring) == NULL)
    {
        const QFileInfo fileInfo(getOpenedFilePath());
        xccdf_tailoring_set_benchmark_ref(mTailoring, fileInfo.absoluteFilePath().toUtf8().constData());
    }


    struct xccdf_benchmark* benchmark = getXCCDFInputBenchmark();
    const struct xccdf_version_info* version_info = xccdf_benchmark_get_schema_version(benchmark);

    if (xccdf_tailoring_export(
        mTailoring,
        path.toUtf8().constData(),
        version_info
    ) != 1) // 1 is actually success here, big inconsistency in openscap API :(
    {
        throw ScanningSessionException(
            QString("Exporting customization to '%1' failed! Details follow:\n%2").arg(path).arg(oscapErrDesc())
        );
    }

    // Keep path if it's a user provided path
    if (userFile)
        mUserTailoringFile = path;
}

QString ScanningSession::getTailoringFilePath()
{
    if (mTailoringFile.isOpen())
        mTailoringFile.close();

    mTailoringFile.open();
    mTailoringFile.close();

    const QString fileName = mTailoringFile.fileName();
    saveTailoring(fileName, false);

    return fileName;
}

QString ScanningSession::getUserTailoringFilePath()
{
    if (hasTailoring())
    {
        if (!mUserTailoringFile.isEmpty())
            return mUserTailoringFile;
        return getTailoringFilePath();
    }
    return QString();
}

void ScanningSession::generateGuide(const QString& path)
{
    // TODO: This does not deal with multiple datastreams inside one file!

    const QByteArray profileId = getProfile().toUtf8();
    const char* params[] = {
        "profile_id",        profileId.constData(),
        "template",          0,
        "verbosity",         "",
        "hide-profile-info", "yes",
        0
    };

    if (oscap_apply_xslt(getOpenedFilePath().toUtf8().constData(), "xccdf-guide.xsl", path.toUtf8().constData(), params) == -1)
        throw ScanningSessionException(QString("ScanningSession::generateGuide failed! oscap_err_desc(): %1.").arg(oscap_err_desc()));
}

QString ScanningSession::getGuideFilePath()
{
    if (mGuideFile.isOpen())
        mGuideFile.close();

    mGuideFile.open();
    mGuideFile.close();

    const QString fileName = mGuideFile.fileName();
    generateGuide(fileName);

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

std::map<QString, struct xccdf_profile*> ScanningSession::getAvailableProfiles()
{
    std::map<QString, struct xccdf_profile*> ret;

    struct xccdf_policy_model* pmodel = xccdf_session_get_policy_model(getXCCDFSession());

    struct xccdf_tailoring* tailoring = xccdf_policy_model_get_tailoring(pmodel);
    if (tailoring)
    {
        struct xccdf_profile_iterator* profile_it = xccdf_tailoring_get_profiles(tailoring);
        while (xccdf_profile_iterator_has_more(profile_it))
        {
            struct xccdf_profile* profile = xccdf_profile_iterator_next(profile_it);
            const QString profile_id = QString::fromUtf8(xccdf_profile_get_id(profile));

            assert(ret.find(profile_id) == ret.end());

            ret.insert(
                std::make_pair(
                    profile_id,
                    profile
                )
            );
        }
        xccdf_profile_iterator_free(profile_it);
    }

    struct xccdf_benchmark* benchmark = xccdf_policy_model_get_benchmark(pmodel);
    assert(benchmark);

    struct xccdf_profile_iterator* profile_it = xccdf_benchmark_get_profiles(benchmark);
    while (xccdf_profile_iterator_has_more(profile_it))
    {
        struct xccdf_profile* profile = xccdf_profile_iterator_next(profile_it);
        const QString profile_id = QString::fromUtf8(xccdf_profile_get_id(profile));

        // Only insert the profile if it's not being shadowed by a profile from tailoring
        if (ret.find(profile_id) == ret.end())
        {
            ret.insert(
                std::make_pair(
                    profile_id,
                    profile
                )
            );
        }
    }
    xccdf_profile_iterator_free(profile_it);

    return ret;
}

void ScanningSession::setProfile(const QString& profileID)
{
    if (!fileOpened())
        throw ScanningSessionException(QString("File hasn't been opened, can't set profile to '%1'").arg(profileID));

    reloadSession();

    if (!xccdf_session_set_profile_id(mSession, profileID.isEmpty() ? NULL : profileID.toUtf8().constData()))
        throw ScanningSessionException(QString("Failed to set profile ID to '%1'. oscap error: %2").arg(profileID).arg(oscapErrDesc()));
}

QString ScanningSession::getProfile() const
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
                QString("Failed to reload session. OpenSCAP error message:\n%1").arg(oscapErrGetFullError()));

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

struct xccdf_profile* ScanningSession::tailorCurrentProfile(bool shadowed, const QString& newIdBase)
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

            oscap_text_set_text(newTitle, (QString::fromUtf8(oscap_text_get_text(oldTitle)) + QString(" [CUSTOMIZED]")).toUtf8().constData());
            oscap_text_set_overrides(newTitle, true);
            xccdf_profile_add_title(newProfile, newTitle);
        }
        oscap_text_iterator_free(titles);

        struct oscap_text_iterator* descs = xccdf_profile_get_description(oldProfile);
        while (oscap_text_iterator_has_more(descs))
        {
            struct oscap_text* oldDesc = oscap_text_iterator_next(descs );
            struct oscap_text* newDesc = oscap_text_clone(oldDesc);

            oscap_text_set_overrides(newDesc, true);
            xccdf_profile_add_description(newProfile, newDesc);
        }
        oscap_text_iterator_free(descs);
    }
    else
    {
        xccdf_profile_set_id(newProfile, newIdBase.toUtf8().constData());

        {
            struct oscap_text* newTitle = oscap_text_new();
            oscap_text_set_lang(newTitle, OSCAP_LANG_ENGLISH_US);
            oscap_text_set_text(newTitle, "(default) [CUSTOMIZED]");
            oscap_text_set_overrides(newTitle, true);
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

const struct xccdf_version_info* ScanningSession::getXCCDFVersionInfo()
{
    struct xccdf_benchmark* benchmark = getXCCDFInputBenchmark();
    if (!benchmark)
        return 0;

    return xccdf_benchmark_get_schema_version(benchmark);
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
