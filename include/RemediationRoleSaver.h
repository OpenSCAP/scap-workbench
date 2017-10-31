/*
 * Copyright 2017 Red Hat Inc., Durham, North Carolina.
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
 *      Matej Tyc <matyc@redhat.com>
 */

#ifndef SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_
#define SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_

#include <QString>
#include <QFileDialog>

#include "ScanningSession.h"
#include "OscapScannerLocal.h"


/// Base for all remediation generators
class RemediationSaverBase
{
    public:
        RemediationSaverBase(QWidget* parentWindow,
                const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType);
        void selectFilenameAndSaveRole();

    protected:
        void saveFileError(const QString& filename, const QString& error_msg);
        void saveFileOK(const QString& filename);

        QWidget* mParentWindow;

        QString mSaveMessage;
        QString mFiletypeExtension;
        QString mFiletypeTemplate;
        QString mFixType;

    private:
        virtual void saveToFile(const QString& filename) = 0;
        QString guessFilenameStem() const;
};


/// Base for all profile-based remediation generators
class ProfileBasedRemediationSaver : public RemediationSaverBase
{
    public:
        ProfileBasedRemediationSaver(QWidget* parentWindow, ScanningSession* session,
                const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType);

    private:
        virtual void saveToFile(const QString& filename);
        const ScanningSession* mScanningSession;
};


class BashProfileRemediationSaver : public ProfileBasedRemediationSaver
{
    public:
        BashProfileRemediationSaver(QWidget* parentWindow, ScanningSession* session);
};


class AnsibleProfileRemediationSaver : public ProfileBasedRemediationSaver
{
    public:
        AnsibleProfileRemediationSaver(QWidget* parentWindow, ScanningSession* session);
};


class PuppetProfileRemediationSaver : public ProfileBasedRemediationSaver
{
    public:
        PuppetProfileRemediationSaver(QWidget* parentWindow, ScanningSession* session);
};


/// Base for all result-based remediation generators that uses the openscap library
class ResultBasedLibraryRemediationSaver : public RemediationSaverBase
{
    public:
        ResultBasedLibraryRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents,
                const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType);

    private:
        virtual void saveToFile(const QString& filename);
        QTemporaryFile mArfFile;
};


/// Base for all result-based remediation generators that uses oscap process
class ResultBasedProcessRemediationSaver : public RemediationSaverBase
{
    public:
        ResultBasedProcessRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents,
                const QString& saveMessage, const QString& filetypeExtension, const QString& filetypeTemplate, const QString& fixType);

    private:
        virtual void saveToFile(const QString& filename);
        QTemporaryFile mArfFile;
        QWidget mParentWindow;
};


class BashResultRemediationSaver : public ResultBasedLibraryRemediationSaver
{
    public:
        BashResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents);
};


class AnsibleResultRemediationSaver : public ResultBasedProcessRemediationSaver
{
    public:
        AnsibleResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents);
};


class PuppetResultRemediationSaver : public ResultBasedProcessRemediationSaver
{
    public:
        PuppetResultRemediationSaver(QWidget* parentWindow, const QByteArray& arfContents);
};


#endif // SCAP_WORKBENCH_REMEDIATION_ROLE_SAVER_H_
